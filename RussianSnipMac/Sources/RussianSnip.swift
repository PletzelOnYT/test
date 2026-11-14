import AppKit
import SwiftUI
import Vision
import AVFoundation
import Carbon

@main
struct RussianSnipApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var state = SnipState.shared

    var body: some Scene {
        WindowGroup("Russian Snip") {
            MainView(state: state)
                .frame(minWidth: 750, minHeight: 570)
        }
        .defaultSize(width: 960, height: 710)
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("Snip & Translate") { state.snip() }
                    .keyboardShortcut("r", modifiers: [.control, .option])
            }
        }
        MenuBarExtra("Russian Snip", systemImage: "text.viewfinder") {
            Button("Snip & Translate (⌃⌥R)") { state.snip() }
            Button("Show Window") { SnipState.showWindow() }
            Divider()
            Button("Quit") { NSApp.terminate(nil) }
        }
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var hotKey: EventHotKeyRef?
    private var handlerRef: EventHandlerRef?
    func applicationDidFinishLaunching(_ notification: Notification) {
        var event = EventTypeSpec(eventClass: OSType(kEventClassKeyboard),
                                  eventKind: UInt32(kEventHotKeyPressed))
        let callback: EventHandlerUPP = { _, _, _ in
            DispatchQueue.main.async { Task { @MainActor in SnipState.shared.snip() } }
            return noErr
        }
        InstallEventHandler(GetApplicationEventTarget(), callback, 1, &event, nil, &handlerRef)
        let id = EventHotKeyID(signature: OSType(0x52534E50), id: 1)
        RegisterEventHotKey(UInt32(kVK_ANSI_R), UInt32(controlKey | optionKey),
                            id, GetApplicationEventTarget(), 0, &hotKey)
    }
    func applicationWillTerminate(_ notification: Notification) {
        if let hotKey { UnregisterEventHotKey(hotKey) }
        if let handlerRef { RemoveEventHandler(handlerRef) }
    }
}

enum SnipFailure: LocalizedError {
    case noText, unsupportedLanguage, service(String)
    var errorDescription: String? {
        switch self {
        case .noText: return "No text found. Try selecting a larger, sharper region."
        case .unsupportedLanguage: return "Russian OCR is unavailable on this macOS installation."
        case .service(let detail): return "Translation service: " + detail
        }
    }
}

@MainActor
final class SnipState: ObservableObject {
    static let shared = SnipState()
    @Published var russian = ""
    @Published var english = ""
    @Published var reading = ""
    @Published var status = "Ready. Press Control–Option–R to select Russian text."
    @Published var error: String?
    @Published var image: NSImage?
    @Published var capturing = false
    @Published var showingCrop = false
    @Published var cropSource: NSImage?
    @Published var awaitingClipboard = false
    private var pickerHolder: AnyObject?
    private var clipboardTimer: Timer?
    private var clipboardStarted: Date?
    private var clipboardChange = 0
    @Published var translating = false
    @Published var checkingProviders = false
    @Published var engineUsed = "Not translated yet"
    @Published var fallbackReport: [String] = []
    @Published var providerChecks: [String] = []
    @Published var mode: ProviderMode = ProviderMode(rawValue:
        UserDefaults.standard.string(forKey: "providerMode") ?? "") ?? .automatic {
        didSet { UserDefaults.standard.set(mode.rawValue, forKey: "providerMode") }
    }
    @Published var allowCommunity: Bool =
        (UserDefaults.standard.object(forKey: "allowCommunity") as? Bool) ?? true {
        didSet { UserDefaults.standard.set(allowCommunity, forKey: "allowCommunity") }
    }
    @Published var preferApple: Bool =
        (UserDefaults.standard.object(forKey: "preferApple") as? Bool) ?? true {
        didSet { UserDefaults.standard.set(preferApple, forKey: "preferApple") }
    }
    private let speaker = AVSpeechSynthesizer()
    private init() {}

    static func showWindow() {
        NSApp.unhide(nil)
        NSApp.activate(ignoringOtherApps: true)
        NSApp.windows.first(where: { $0.canBecomeKey && !($0 is NSPanel) })?.makeKeyAndOrderFront(nil)
    }

    func snip() {
        guard !capturing && !translating && !awaitingClipboard && !showingCrop else { return }
        error = nil
        status = "Choose a window or display in Apple's picker. No Screen Recording permission required."
        if #available(macOS 14.0, *) {
            capturing = true
            let picker = PermissionlessScreenPicker()
            pickerHolder = picker
            picker.begin(onImage: { [weak self] picture in
                guard let self else { return }
                self.pickerHolder = nil
                self.capturing = false
                self.cropSource = picture
                self.showingCrop = true
                self.status = "Drag to select the Russian text."
                Self.showWindow()
            }, onFailure: { [weak self] explanation in
                guard let self else { return }
                self.pickerHolder = nil
                self.capturing = false
                self.error = explanation
                self.status = "Use the clipboard screenshot option if the picker is unavailable."
                Self.showWindow()
            })
        } else {
            waitForSystemScreenshot()
        }
    }

    // Uses macOS's own trusted screenshot shortcut. Requires ZERO app permissions.
    func waitForSystemScreenshot() {
        guard !capturing && !translating && !awaitingClipboard else { return }
        error = nil
        awaitingClipboard = true
        clipboardChange = NSPasteboard.general.changeCount
        clipboardStarted = Date()
        status = "Press Control + Command + Shift + 4, select an area; this app will recognize it automatically."
        clipboardTimer?.invalidate()
        clipboardTimer = Timer.scheduledTimer(withTimeInterval: 0.35, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.checkClipboard() }
        }
        Task {
            try? await Task.sleep(nanoseconds: 850_000_000)
            if awaitingClipboard { NSApp.hide(nil) }
        }
    }

    private func checkClipboard() {
        guard awaitingClipboard else { return }
        if let started = clipboardStarted, Date().timeIntervalSince(started) > 45 {
            stopClipboardWatch()
            Self.showWindow()
            status = "Clipboard screenshot timed out. Try again, or click Paste Screenshot."
            return
        }
        let pasteboard = NSPasteboard.general
        guard pasteboard.changeCount != clipboardChange else { return }
        clipboardChange = pasteboard.changeCount
        guard let pasted = imageFromClipboard() else { return }
        stopClipboardWatch()
        Self.showWindow()
        receiveImage(pasted)
    }

    private func stopClipboardWatch() {
        clipboardTimer?.invalidate()
        clipboardTimer = nil
        clipboardStarted = nil
        awaitingClipboard = false
    }

    private func imageFromClipboard() -> NSImage? {
        let clipboard = NSPasteboard.general
        if let image = clipboard.readObjects(forClasses: [NSImage.self], options: nil)?.first as? NSImage {
            return image
        }
        if let data = clipboard.data(forType: .png) ?? clipboard.data(forType: .tiff) {
            return NSImage(data: data)
        }
        return nil
    }

    func pasteScreenshot() {
        guard !translating && !capturing else { return }
        if let result = imageFromClipboard() {
            stopClipboardWatch()
            Self.showWindow()
            receiveImage(result)
        } else {
            error = "No screenshot image on clipboard. Press Control + Command + Shift + 4, drag a region, then click Paste Screenshot."
        }
    }

    private func receiveImage(_ image: NSImage) {
        error = nil
        cropSource = image
        showingCrop = true
        status = "Drag a box around the words or choose Use Full Image."
    }

    func cancelCrop() {
        showingCrop = false
        cropSource = nil
        status = "Ready. Use Snip & Translate or Paste Screenshot."
    }

    func acceptCrop(_ picture: NSImage) {
        showingCrop = false
        cropSource = nil
        capturing = true
        image = picture
        status = "Recognizing selected text locally…"
        Task {
            let filename = "RussianSnip-OCR-" + UUID().uuidString + ".png"
            let url = FileManager.default.temporaryDirectory.appendingPathComponent(filename)
            defer { try? FileManager.default.removeItem(at: url) }
            do {
                guard let tiff = picture.tiffRepresentation,
                      let rep = NSBitmapImageRep(data: tiff),
                      let png = rep.representation(using: .png, properties: [:]) else {
                    throw SnipFailure.noText
                }
                try png.write(to: url, options: .atomic)
                let result = try await Task.detached(priority: .userInitiated) {
                    try TextRecognizer.read(url)
                }.value
                guard !result.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                    throw SnipFailure.noText
                }
                russian = result
                reading = Romanizer.convert(result)
                english = ""
                capturing = false
                translate()
            } catch {
                self.error = error.localizedDescription
                status = "Unable to recognize text in that region."
                capturing = false
            }
        }
    }

    func sourceEdited() {
        reading = Romanizer.convert(russian)
        english = ""
    }

    func example() {
        guard !capturing && !translating else { return }
        russian = "Через сто лет в Москве будет жить девочка Алиса Селезнёва."
        reading = Romanizer.convert(russian)
        english = ""
        image = nil
        error = nil
        status = "Sample ready. Click Translate."
    }

    func translate() {
        guard !capturing && !translating else { return }
        let text = russian.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else {
            error = "First capture or type some Russian text."
            return
        }
        translating = true
        error = nil
        fallbackReport = []
        engineUsed = "Selecting a provider…"
        status = "Finding a working Russian-to-English translator…"
        let settings = EngineSettings.fromStorage(
            mode: mode, allowCommunity: allowCommunity, preferApple: preferApple
        )
        Task {
            do {
                let result = try await SmartTranslate.translate(text, settings: settings) { [weak self] name in
                    Task { @MainActor in
                        guard let self = self, self.translating else { return }
                        self.status = "Trying " + name + "…"
                    }
                }
                if text == russian.trimmingCharacters(in: .whitespacesAndNewlines) {
                    english = result.text
                    engineUsed = result.provider
                    fallbackReport = result.reports
                    status = "Translated using " + result.provider + "."
                } else {
                    status = "Original text changed; translate again."
                }
            } catch {
                self.error = error.localizedDescription
                engineUsed = "No provider available"
                status = "Online translators unavailable. OCR and pronunciation remain functional."
            }
            translating = false
        }
    }

    func checkProviders() {
        guard !checkingProviders && !capturing && !translating else { return }
        checkingProviders = true
        providerChecks = []
        let settings = EngineSettings.fromStorage(
            mode: mode, allowCommunity: allowCommunity, preferApple: preferApple
        )
        Task {
            let results = await SmartTranslate.testAll(settings: settings) { [weak self] name in
                Task { @MainActor in self?.status = "Checking " + name + "…" }
            }
            providerChecks = results
            checkingProviders = false
            status = "Provider checks finished. These are connectivity tests, not quality scores."
        }
    }

    func speak() {
        guard !russian.isEmpty else { return }
        speaker.stopSpeaking(at: .immediate)
        let phrase = AVSpeechUtterance(string: russian)
        phrase.voice = AVSpeechSynthesisVoice(language: "ru-RU")
        phrase.rate = 0.45
        speaker.speak(phrase)
    }

    func copy(_ value: String) {
        guard !value.isEmpty else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(value, forType: .string)
        status = "Copied to clipboard."
    }
}

enum TextRecognizer {
    static func read(_ url: URL) throws -> String {
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = true
        let languages = try request.supportedRecognitionLanguages()
        guard languages.contains("ru-RU") else { throw SnipFailure.unsupportedLanguage }
        request.recognitionLanguages = languages.contains("en-US") ? ["ru-RU", "en-US"] : ["ru-RU"]
        let handler = VNImageRequestHandler(url: url, options: [:])
        try handler.perform([request])
        let lines = (request.results ?? []).sorted {
            let y = $0.boundingBox.midY - $1.boundingBox.midY
            return abs(y) > 0.012 ? y > 0 : $0.boundingBox.minX < $1.boundingBox.minX
        }
        guard !lines.isEmpty else { throw SnipFailure.noText }
        var output = ""
        for line in lines {
            guard let top = line.topCandidates(1).first else { continue }
            let value = top.string.trimmingCharacters(in: .whitespacesAndNewlines)
            if value.isEmpty { continue }
            if !output.isEmpty {
                if output.hasSuffix("-") && value.first?.isLetter == true {
                    output.removeLast()
                } else { output += " " }
            }
            output += value
        }
        return output
    }
}

enum Romanizer {
    private static let alphabet: [Character: String] = [
        "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"yo",
        "ж":"zh","з":"z","и":"i","й":"y","к":"k","л":"l","м":"m",
        "н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u",
        "ф":"f","х":"kh","ц":"ts","ч":"ch","ш":"sh","щ":"shch",
        "ъ":"","ы":"y","ь":"'","э":"e","ю":"yu","я":"ya"
    ]
    private static let vowels = Set<Character>("аеёиоуыэюяьъ")
    static func convert(_ text: String) -> String {
        let input = Array(text)
        var result = ""
        for i in input.indices {
            let char = input[i]
            let lower = Character(String(char).lowercased())
            guard var output = alphabet[lower] else {
                result.append(char)
                continue
            }
            if lower == "е" {
                let start = i == 0 || !input[i-1].isLetter
                let afterVowel = i > 0 && vowels.contains(Character(String(input[i-1]).lowercased()))
                if start || afterVowel { output = "ye" }
            }
            if char.isUppercase {
                output = output.prefix(1).uppercased() + output.dropFirst()
            }
            result += output
        }
        return result
    }
}


struct MainView: View {
    @ObservedObject var state: SnipState

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                if #available(macOS 15.0, *) {
                    AppleTranslationHost()
                }
                HStack(spacing: 12) {
                    Image(systemName: "text.viewfinder")
                        .font(.system(size: 30, weight: .bold))
                        .foregroundStyle(.white)
                        .frame(width: 62, height: 62)
                        .background(.indigo, in: RoundedRectangle(cornerRadius: 15))
                    VStack(alignment: .leading, spacing: 5) {
                        Text("Russian Snip").font(.system(size: 29, weight: .bold))
                        Text("Select Russian on your screen, translate, and learn how to say it.")
                            .font(.subheadline).foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                HStack(spacing: 12) {
                    Button { state.snip() } label: { Label("Snip & Translate", systemImage: "crop") }
                        .buttonStyle(.borderedProminent).tint(.indigo)
                        .disabled(state.capturing || state.translating)
                    Button { state.waitForSystemScreenshot() } label: {
                        Label("No-Permission Snip", systemImage: "rectangle.dashed")
                    }
                    .disabled(state.awaitingClipboard || state.capturing || state.translating)
                    Button { state.pasteScreenshot() } label: {
                        Label("Paste Screenshot", systemImage: "doc.on.clipboard")
                    }
                    .disabled(state.capturing || state.translating)
                    Button("Translate again") { state.translate() }
                        .disabled(state.capturing || state.translating || state.russian.isEmpty)
                    Button("Try example") { state.example() }
                    Spacer()
                    Text("⌃⌥R").font(.system(.subheadline, design: .monospaced))
                }
                HStack {
                    if state.capturing || state.translating || state.awaitingClipboard { ProgressView().controlSize(.small) }
                    Text(state.status).font(.callout).foregroundStyle(.secondary)
                }
                if let error = state.error {
                    Text(error).foregroundStyle(.orange).textSelection(.enabled)
                }
                if state.awaitingClipboard {
                    Text("Press Control + Command + Shift + 4, then drag across Russian text. The app detects the clipboard screenshot.")
                        .font(.callout).foregroundStyle(.secondary)
                }
                HStack(alignment: .top, spacing: 14) {
                    card("Original Russian", badge: "OFFLINE OCR") {
                        TextEditor(text: $state.russian)
                            .font(.system(size: 16))
                            .scrollContentBackground(.hidden)
                            .onChange(of: state.russian) { _ in state.sourceEdited() }
                            .frame(minHeight: 240)
                        HStack {
                            Button { state.speak() } label: {
                                Label("Speak Russian", systemImage: "speaker.wave.2")
                            }.disabled(state.russian.isEmpty)
                            Spacer()
                            Button("Copy") { state.copy(state.russian) }
                        }
                    }
                    card("English Translation", badge: "SMART FAILOVER") {
                        ScrollView {
                            Text(state.english.isEmpty ? "The English translation appears here." : state.english)
                                .font(.system(size: 16))
                                .foregroundStyle(state.english.isEmpty ? .secondary : .primary)
                                .textSelection(.enabled)
                                .frame(maxWidth: .infinity, alignment: .topLeading)
                        }.frame(minHeight: 240)
                        HStack {
                            Text("Used: " + state.engineUsed)
                                .font(.caption).foregroundStyle(.secondary)
                            Spacer()
                            Button("Copy") { state.copy(state.english) }
                        }
                    }
                }
                card("How to say it in Russian", badge: "ENGLISH LETTERS") {
                    Text(state.reading.isEmpty ? "Example: Privet! Kak dela?" : state.reading)
                        .font(.system(size: 19, weight: .medium, design: .rounded))
                        .foregroundStyle(state.reading.isEmpty ? .secondary : .primary)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, minHeight: 64, alignment: .topLeading)
                    HStack {
                        Text("Approximate pronunciation; press Speak Russian to hear the real sounds.")
                            .font(.caption).foregroundStyle(.secondary)
                        Spacer()
                        Button("Copy") { state.copy(state.reading) }
                    }
                }
                if !state.fallbackReport.isEmpty {
                    DisclosureGroup("Fallback details (" + String(state.fallbackReport.count) + " failed provider attempts)") {
                        VStack(alignment: .leading, spacing: 4) {
                            ForEach(state.fallbackReport, id: \.self) { item in
                                Text(item).font(.caption).foregroundStyle(.secondary).textSelection(.enabled)
                            }
                        }.padding(.top, 8)
                    }
                }
                ProviderSettingsView(state: state)
                Divider()
                Text("Capture fix: Apple user-selected window/display picker on macOS 14+ (no global Screen Recording permission), plus a built-in clipboard screenshot method on all supported Macs. No screencapture subprocess. Privacy: Screenshots are recognized locally. Apple on-device translation (macOS 15+) stays on your Mac when language packs are installed. Online providers receive only the recognized text, not your screenshot. Community mirrors are independently operated, may go offline, and are not vetted for private documents. Optional keys are stored in macOS Keychain. The app is ad-hoc signed, not Apple-notarized.")
                    .font(.caption).foregroundStyle(.secondary)
            }.padding(24)
        }
        .sheet(isPresented: $state.showingCrop) {
            if let picture = state.cropSource {
                ScreenshotCropSheet(image: picture, accept: { cropped in
                    state.acceptCrop(cropped)
                }, cancel: {
                    state.cancelCrop()
                })
            }
        }
    }

    private func card<Content: View>(_ heading: String,
                                     badge: String,
                                     @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(heading).font(.headline)
                Spacer()
                Text(badge).font(.system(size: 10, weight: .bold))
                    .foregroundStyle(.secondary)
            }
            content()
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 14))
    }
}


struct ProviderSettingsView: View {
    @ObservedObject var state: SnipState
    @State private var expanded = false
    @State private var deeplKey = SecretVault.get("deepl")
    @State private var azureKey = SecretVault.get("azure")
    @State private var azureRegion = UserDefaults.standard.string(forKey: "azureRegion") ?? ""
    @State private var googleKey = SecretVault.get("google")
    @State private var libreURL = UserDefaults.standard.string(forKey: "libreURL") ?? ""
    @State private var libreKey = SecretVault.get("libre")
    @State private var memoryEmail = UserDefaults.standard.string(forKey: "memoryEmail") ?? ""
    @State private var saveResult = ""

    var body: some View {
        DisclosureGroup(isExpanded: $expanded) {
            VStack(alignment: .leading, spacing: 12) {
                Picker("Translation engine", selection: $state.mode) {
                    ForEach(ProviderMode.allCases) { item in
                        Text(item.rawValue).tag(item)
                    }
                }.pickerStyle(.menu)
                Text("Automatic mode tries configured premium/official providers, optional offline Apple translation, MyMemory, then public LibreTranslate mirrors. Unavailable or untranslated responses are rejected.")
                    .font(.caption).foregroundStyle(.secondary)
                Toggle("Try Apple on-device translation first (macOS 15+, installed languages)", isOn: $state.preferApple)
                Toggle("Use community LibreTranslate mirrors as last-resort backups", isOn: $state.allowCommunity)
                Text("Community mirrors are independently operated. Their availability and privacy policies can change. Disable this for sensitive text.")
                    .font(.caption).foregroundStyle(.secondary)
                HStack {
                    Button(state.checkingProviders ? "Checking…" : "Check provider connections") {
                        state.checkProviders()
                    }.disabled(state.checkingProviders || state.translating)
                    Spacer()
                    Text("Test uses a sample sentence, not your screenshot")
                        .font(.caption).foregroundStyle(.secondary)
                }
                if !state.providerChecks.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(state.providerChecks, id: \.self) { item in
                            Text(item).font(.caption).textSelection(.enabled)
                        }
                    }
                }
                Divider()
                Text("Optional API keys & custom server").font(.headline)
                Text("Leave these blank for no-account operation. Some cloud APIs can bill above their free allowance; check your provider plan.")
                    .font(.caption).foregroundStyle(.secondary)
                SecureField("DeepL API Developer / Free key (optional)", text: $deeplKey)
                    .textFieldStyle(.roundedBorder)
                HStack {
                    SecureField("Microsoft Azure Translator key (optional)", text: $azureKey)
                    TextField("Azure region (if required)", text: $azureRegion)
                }.textFieldStyle(.roundedBorder)
                SecureField("Google Cloud Translation API key (optional)", text: $googleKey)
                    .textFieldStyle(.roundedBorder)
                TextField("Custom LibreTranslate HTTPS base URL (optional)", text: $libreURL)
                    .textFieldStyle(.roundedBorder)
                SecureField("Custom LibreTranslate API key (optional)", text: $libreKey)
                    .textFieldStyle(.roundedBorder)
                TextField("MyMemory contact email, optional (increases published quota)", text: $memoryEmail)
                    .textFieldStyle(.roundedBorder)
                HStack {
                    Button("Save provider settings") {
                        let results = [
                            SecretVault.set("deepl", value: deeplKey.trimmingCharacters(in: .whitespacesAndNewlines)),
                            SecretVault.set("azure", value: azureKey.trimmingCharacters(in: .whitespacesAndNewlines)),
                            SecretVault.set("google", value: googleKey.trimmingCharacters(in: .whitespacesAndNewlines)),
                            SecretVault.set("libre", value: libreKey.trimmingCharacters(in: .whitespacesAndNewlines))
                        ]
                        UserDefaults.standard.set(azureRegion.trimmingCharacters(in: .whitespacesAndNewlines), forKey: "azureRegion")
                        UserDefaults.standard.set(libreURL.trimmingCharacters(in: .whitespacesAndNewlines), forKey: "libreURL")
                        UserDefaults.standard.set(memoryEmail.trimmingCharacters(in: .whitespacesAndNewlines), forKey: "memoryEmail")
                        state.providerChecks = []
                        saveResult = results.allSatisfy { $0 } ? "Saved to Keychain and preferences." : "Could not save one or more keys to Keychain."
                    }.buttonStyle(.borderedProminent)
                    if !saveResult.isEmpty {
                        Text(saveResult).font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
            .padding(.top, 12)
        } label: {
            Label("Translation providers, API keys & diagnostics", systemImage: "server.rack")
                .font(.headline)
        }
        .padding(16)
        .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 14))
    }
}
