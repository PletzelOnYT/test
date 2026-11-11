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
    @Published var translating = false
    private let speaker = AVSpeechSynthesizer()
    private init() {}

    static func showWindow() {
        NSApp.unhide(nil)
        NSApp.activate(ignoringOtherApps: true)
        NSApp.windows.first(where: { $0.canBecomeKey && !($0 is NSPanel) })?.makeKeyAndOrderFront(nil)
    }

    func snip() {
        guard !capturing && !translating else { return }
        capturing = true
        error = nil
        status = "Drag to select Russian text. Press Esc to cancel."
        Task { await takeScreenshot() }
    }

    private func takeScreenshot() async {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("RussianSnip-" + UUID().uuidString + ".png")
        defer { try? FileManager.default.removeItem(at: url) }
        NSApp.hide(nil)
        try? await Task.sleep(nanoseconds: 300_000_000)
        do {
            let code = try await Task.detached(priority: .userInitiated) { () -> Int32 in
                let task = Process()
                task.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
                task.arguments = ["-x", "-i", "-s", url.path]
                try task.run()
                task.waitUntilExit()
                return task.terminationStatus
            }.value
            Self.showWindow()
            guard code == 0 && FileManager.default.fileExists(atPath: url.path) else {
                status = "Selection cancelled."
                capturing = false
                return
            }
            image = NSImage(contentsOf: url)
            status = "Recognizing Russian locally…"
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
            Self.showWindow()
            self.error = error.localizedDescription
            status = "Unable to read selection."
            capturing = false
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
        status = "Translating Russian into English…"
        Task {
            do {
                let answer = try await MyMemory.translate(text)
                if text == russian.trimmingCharacters(in: .whitespacesAndNewlines) {
                    english = answer
                    status = "Done. Translation and pronunciation ready."
                } else {
                    status = "Text changed; translate again."
                }
            } catch {
                self.error = error.localizedDescription
                status = "Translation unavailable. Offline OCR and pronunciation still work."
            }
            translating = false
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

enum MyMemory {
    struct Result: Decodable {
        struct DataItem: Decodable { let translatedText: String? }
        let responseData: DataItem?
        let responseStatus: Int?
        let responseDetails: String?
    }
    static func split(_ input: String) -> [String] {
        var parts: [String] = []
        var current = ""
        for character in input {
            let next = current + String(character)
            if next.utf8.count > 430 && !current.isEmpty {
                parts.append(current)
                current = ""
            }
            current.append(character)
        }
        if !current.isEmpty { parts.append(current) }
        return parts
    }
    static func translate(_ input: String) async throws -> String {
        var parts: [String] = []
        for chunk in split(input) {
            var url = URLComponents(string: "https://api.mymemory.translated.net/get")!
            url.queryItems = [
                URLQueryItem(name: "q", value: chunk),
                URLQueryItem(name: "langpair", value: "ru|en")
            ]
            var request = URLRequest(url: url.url!)
            request.timeoutInterval = 25
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw SnipFailure.service("Server error or rate limit reached.")
            }
            let parsed = try JSONDecoder().decode(Result.self, from: data)
            guard parsed.responseStatus == 200, let text = parsed.responseData?.translatedText,
                  !text.isEmpty else {
                throw SnipFailure.service(parsed.responseDetails ?? "Daily quota reached.")
            }
            var clean = text
            for (a, b) in [("&quot;", "\""), ("&#39;", "'"), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">")] {
                clean = clean.replacingOccurrences(of: a, with: b)
            }
            parts.append(clean)
        }
        return parts.joined()
    }
}

struct MainView: View {
    @ObservedObject var state: SnipState

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
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
                    Button("Translate again") { state.translate() }
                        .disabled(state.capturing || state.translating || state.russian.isEmpty)
                    Button("Try example") { state.example() }
                    Spacer()
                    Text("⌃⌥R").font(.system(.subheadline, design: .monospaced))
                }
                HStack {
                    if state.capturing || state.translating { ProgressView().controlSize(.small) }
                    Text(state.status).font(.callout).foregroundStyle(.secondary)
                }
                if let error = state.error {
                    Text(error).foregroundStyle(.orange).textSelection(.enabled)
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
                    card("English Translation", badge: "FREE API") {
                        ScrollView {
                            Text(state.english.isEmpty ? "The English translation appears here." : state.english)
                                .font(.system(size: 16))
                                .foregroundStyle(state.english.isEmpty ? .secondary : .primary)
                                .textSelection(.enabled)
                                .frame(maxWidth: .infinity, alignment: .topLeading)
                        }.frame(minHeight: 240)
                        HStack {
                            Text("MyMemory · internet required")
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
                Divider()
                Text("Privacy: screenshots are processed and deleted locally. Only recognized text is sent to the free translation service. The service has a daily limit. Screen Recording permission may be required.")
                    .font(.caption).foregroundStyle(.secondary)
            }.padding(24)
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
