import AppKit
import Foundation
import Security
import Translation
import SwiftUI

enum ProviderMode: String, CaseIterable, Identifiable {
    case automatic = "Automatic failover"
    case apple = "Apple On-Device"
    case deepl = "DeepL API"
    case microsoft = "Microsoft Translator"
    case google = "Google Cloud Translate"
    case myMemory = "MyMemory"
    case privateLibre = "Custom LibreTranslate"
    case community = "Community LibreTranslate"
    var id: String { rawValue }
}

enum SecretVault {
    private static let service = "app.russiansnip.desktop.translation.v2"

    static func get(_ name: String) -> String {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: name,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data,
              let value = String(data: data, encoding: .utf8) else { return "" }
        return value
    }

    @discardableResult
    static func set(_ name: String, value: String) -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: name
        ]
        SecItemDelete(query as CFDictionary)
        if value.isEmpty { return true }
        var attrs = query
        attrs[kSecValueData as String] = Data(value.utf8)
        attrs[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        return SecItemAdd(attrs as CFDictionary, nil) == errSecSuccess
    }
}

struct EngineSettings {
    var mode: ProviderMode = .automatic
    var allowCommunity: Bool = true
    var preferApple: Bool = true
    var deeplKey: String = ""
    var azureKey: String = ""
    var azureRegion: String = ""
    var googleKey: String = ""
    var libreURL: String = ""
    var libreKey: String = ""
    var memoryEmail: String = ""

    static func fromStorage(mode: ProviderMode, allowCommunity: Bool, preferApple: Bool) -> Self {
        return EngineSettings(mode: mode,
                              allowCommunity: allowCommunity,
                              preferApple: preferApple,
                              deeplKey: SecretVault.get("deepl"),
                              azureKey: SecretVault.get("azure"),
                              azureRegion: UserDefaults.standard.string(forKey: "azureRegion") ?? "",
                              googleKey: SecretVault.get("google"),
                              libreURL: UserDefaults.standard.string(forKey: "libreURL") ?? "",
                              libreKey: SecretVault.get("libre"),
                              memoryEmail: UserDefaults.standard.string(forKey: "memoryEmail") ?? "")
    }
}

struct EngineResult {
    let text: String
    let provider: String
    let reports: [String]
}

enum EngineError: LocalizedError {
    case noService
    case request(String)
    case quality(String)
    case exhausted([String])

    var errorDescription: String? {
        switch self {
        case .noService: return "No translation engine is configured."
        case .request(let text): return text
        case .quality(let text): return "Output rejected: " + text
        case .exhausted(let failures):
            return "All available translators failed. " + failures.joined(separator: " · ")
        }
    }
}

enum EngineProvider: Equatable {
    case apple
    case deepl
    case azure
    case google
    case myMemory
    case customLibre(String)
    case communityLibre(String)

    var name: String {
        switch self {
        case .apple: return "Apple On-Device"
        case .deepl: return "DeepL"
        case .azure: return "Microsoft Translator"
        case .google: return "Google Cloud"
        case .myMemory: return "MyMemory"
        case .customLibre: return "Custom LibreTranslate"
        case .communityLibre(let host):
            return "LibreTranslate (" + (URL(string: host)?.host ?? "mirror") + ")"
        }
    }
}

enum SmartTranslate {
    // Official LibreTranslate community mirror list, November 2026.
    // These are independent volunteer servers. They may disappear or require keys.
    static let communityHosts = [
        "https://translate.cutie.dating",
        "https://translate.fedilab.app",
        "https://translate.foxhaven.cyou",
        "https://translate.terraprint.co"
    ]

    static func available(_ settings: EngineSettings) -> [EngineProvider] {
        var providers: [EngineProvider] = []
        switch settings.mode {
        case .automatic:
            if !settings.deeplKey.isEmpty { providers.append(.deepl) }
            if settings.preferApple { providers.append(.apple) }
            if !settings.azureKey.isEmpty { providers.append(.azure) }
            if !settings.googleKey.isEmpty { providers.append(.google) }
            if !settings.libreURL.isEmpty { providers.append(.customLibre(settings.libreURL)) }
            providers.append(.myMemory)
            if settings.allowCommunity {
                providers += communityHosts.map { .communityLibre($0) }
            }
        case .apple: providers = [.apple]
        case .deepl: providers = [.deepl]
        case .microsoft: providers = [.azure]
        case .google: providers = [.google]
        case .myMemory: providers = [.myMemory]
        case .privateLibre: providers = [.customLibre(settings.libreURL)]
        case .community:
            providers = communityHosts.map { .communityLibre($0) }
        }
        return providers
    }

    static func translate(_ source: String,
                          settings: EngineSettings,
                          progress: @escaping (String) -> Void = { _ in }) async throws -> EngineResult {
        let input = source.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !input.isEmpty else { throw EngineError.request("There is no text to translate.") }
        let choices = available(settings)
        guard !choices.isEmpty else { throw EngineError.noService }
        var failures: [String] = []
        for provider in choices {
            if Task.isCancelled { throw CancellationError() }
            progress(provider.name)
            do {
                let output = try await run(provider, text: input, settings: settings)
                let accepted = try validate(output, source: input)
                return EngineResult(text: accepted,
                                    provider: provider.name,
                                    reports: failures)
            } catch {
                // Never log or upload source text, account credentials, or server responses.
                let summary = compactFailure(error)
                failures.append(provider.name + ": " + summary)
            }
        }
        throw EngineError.exhausted(failures)
    }

    static func testAll(settings: EngineSettings,
                        progress: @escaping (String) -> Void = { _ in }) async -> [String] {
        let sentence = "Привет! Где находится библиотека?"
        var results: [String] = []
        for provider in available(settings) {
            progress(provider.name)
            do {
                let output = try await run(provider, text: sentence, settings: settings)
                _ = try validate(output, source: sentence)
                results.append("✓ " + provider.name + " — responded successfully")
            } catch {
                results.append("✗ " + provider.name + " — " + compactFailure(error))
            }
        }
        return results
    }

    private static func compactFailure(_ error: Error) -> String {
        if let local = error as? LocalizedError, let detail = local.errorDescription {
            return String(detail.prefix(140))
        }
        if let urlError = error as? URLError {
            switch urlError.code {
            case .timedOut: return "timeout"
            case .cannotFindHost, .cannotConnectToHost, .networkConnectionLost, .notConnectedToInternet:
                return "offline or unreachable"
            default: return "network error (" + String(urlError.code.rawValue) + ")"
            }
        }
        return "unavailable (" + String(describing: type(of: error)) + ")"
    }

    private static func run(_ provider: EngineProvider, text: String,
                            settings: EngineSettings) async throws -> String {
        if provider == .apple {
            if #available(macOS 15.0, *) {
                return try await appleTranslation(text)
            }
            throw EngineError.request("requires macOS 15+")
        }
        let maxBytes = provider == .myMemory ? 430 : 3800
        let chunks = chunk(text, limit: maxBytes)
        var translated: [String] = []
        for piece in chunks {
            if Task.isCancelled { throw CancellationError() }
            let output: String
            switch provider {
            case .apple: throw EngineError.request("Unsupported Apple translation.")
            case .deepl: output = try await deepl(piece, key: settings.deeplKey)
            case .azure: output = try await azure(piece, key: settings.azureKey, region: settings.azureRegion)
            case .google: output = try await google(piece, key: settings.googleKey)
            case .myMemory: output = try await myMemory(piece, email: settings.memoryEmail)
            case .customLibre(let host):
                output = try await libre(piece, host: host, key: settings.libreKey)
            case .communityLibre(let host):
                output = try await libre(piece, host: host, key: "")
            }
            _ = try validate(output, source: piece)
            translated.append(output)
        }
        return translated.joined()
    }

    @available(macOS 15.0, *)
    private static func appleTranslation(_ text: String) async throws -> String {
        return try await AppleTranslationBridge.shared.request(text)
    }

    // Split at spaces/sentence punctuation when possible, keeping every character.
    // MyMemory has a 500-BYTE q limit; every split is bounded by UTF-8 bytes.
    static func chunk(_ text: String, limit: Int) -> [String] {
        guard text.utf8.count > limit else { return [text] }
        var output: [String] = []
        var remainder = text[...]
        while remainder.utf8.count > limit {
            var width = 0
            var boundary = remainder.startIndex
            var lastGood = remainder.startIndex
            while boundary < remainder.endIndex {
                let next = remainder.index(after: boundary)
                let charBytes = remainder[boundary..<next].utf8.count
                if width + charBytes > limit { break }
                width += charBytes
                boundary = next
                let value = remainder[remainder.index(before: boundary)]
                if value == " " || value == "\n" || value == "." || value == "!" || value == "?" {
                    lastGood = boundary
                }
            }
            let consumed = lastGood != remainder.startIndex && width > limit / 2 ? lastGood : boundary
            guard consumed > remainder.startIndex else { break }
            output.append(String(remainder[..<consumed]))
            remainder = remainder[consumed...]
        }
        if !remainder.isEmpty { output.append(String(remainder)) }
        return output
    }

    static func validate(_ result: String, source: String) throws -> String {
        let output = unescape(result).trimmingCharacters(in: .whitespacesAndNewlines)
        guard !output.isEmpty else { throw EngineError.quality("empty translation") }
        let lower = output.lowercased()
        if lower.contains("<html") || lower.contains("<!doctype") ||
           lower.contains("rate limit exceeded") ||
           lower.contains("quota exceeded") ||
           lower.contains("invalid api key") {
            throw EngineError.quality("server returned an error instead of translation")
        }
        let sourceCyrillic = source.unicodeScalars.filter { (0x0400...0x052F).contains($0.value) }.count
        if sourceCyrillic > 2 {
            let cyrillic = output.unicodeScalars.filter { (0x0400...0x052F).contains($0.value) }.count
            let letters = output.unicodeScalars.filter { CharacterSet.letters.contains($0) }.count
            if source.trimmingCharacters(in: .whitespacesAndNewlines) == output ||
               (letters > 3 && Double(cyrillic) / Double(letters) > 0.40) {
                throw EngineError.quality("untranslated Russian text")
            }
        }
        return output
    }

    private static func unescape(_ html: String) -> String {
        var output = html
        let substitutions = [
            "&amp;": "&", "&quot;": "\"", "&#39;": "'",
            "&#x27;": "'", "&apos;": "'", "&lt;": "<", "&gt;": ">", "&nbsp;": " "
        ]
        for (a, b) in substitutions { output = output.replacingOccurrences(of: a, with: b) }
        return output
    }

    private static func json(_ request: URLRequest) async throws -> Any {
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 9
        config.timeoutIntervalForResource = 15
        config.httpCookieStorage = nil
        config.urlCache = nil
        let session = URLSession(configuration: config)
        defer { session.invalidateAndCancel() }
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw EngineError.request("invalid response")
        }
        guard (200...299).contains(http.statusCode) else {
            throw EngineError.request("HTTP " + String(http.statusCode))
        }
        guard data.count < 1_000_000 else { throw EngineError.request("oversized response") }
        do { return try JSONSerialization.jsonObject(with: data) }
        catch { throw EngineError.request("non-JSON response") }
    }

    private static func makeGET(_ url: URL) -> URLRequest {
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 10
        request.setValue("RussianSnip/2.0", forHTTPHeaderField: "User-Agent")
        return request
    }

    private static func makePOST(_ url: URL, body: Any) throws -> URLRequest {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.timeoutInterval = 10
        return request
    }

    private static func myMemory(_ text: String, email: String) async throws -> String {
        var components = URLComponents(string: "https://api.mymemory.translated.net/get")!
        components.queryItems = [
            URLQueryItem(name: "q", value: text),
            URLQueryItem(name: "langpair", value: "ru|en")
        ]
        if email.contains("@"), !email.contains(" ") {
            components.queryItems?.append(URLQueryItem(name: "de", value: email))
        }
        let object = try await json(makeGET(components.url!))
        guard let root = object as? [String: Any] else {
            throw EngineError.request("unexpected MyMemory response")
        }
        let code = (root["responseStatus"] as? Int) ??
                   Int(root["responseStatus"] as? String ?? "0") ?? 0
        if code != 200 {
            throw EngineError.request("MyMemory quota or server error (" + String(code) + ")")
        }
        guard let data = root["responseData"] as? [String: Any],
              let output = data["translatedText"] as? String else {
            throw EngineError.request("MyMemory returned no translation")
        }
        return output
    }

    private static func libre(_ text: String, host: String, key: String) async throws -> String {
        let trimmed = host.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let source = URLComponents(string: trimmed),
              source.scheme == "https", source.host != nil,
              source.user == nil, source.password == nil,
              source.query == nil, source.fragment == nil else {
            throw EngineError.request("LibreTranslate needs a valid https:// URL")
        }
        let path = (source.path.trimmingCharacters(in: CharacterSet(charactersIn: "/")))
        let base = "https://" + source.host! + (source.port.map { ":" + String($0) } ?? "")
        let endpoint = path.hasSuffix("translate") ? base + "/" + path : base + "/" + (path.isEmpty ? "" : path + "/") + "translate"
        guard let url = URL(string: endpoint) else { throw EngineError.request("invalid LibreTranslate endpoint") }
        var body: [String: Any] = ["q": text, "source": "ru", "target": "en", "format": "text"]
        if !key.isEmpty { body["api_key"] = key }
        let object = try await json(makePOST(url, body: body))
        guard let response = object as? [String: Any],
              let output = response["translatedText"] as? String else {
            throw EngineError.request("LibreTranslate returned no translation")
        }
        return output
    }

    private static func deepl(_ text: String, key: String) async throws -> String {
        guard !key.isEmpty else { throw EngineError.request("DeepL key not configured") }
        let host = key.hasSuffix(":fx") ? "https://api-free.deepl.com" : "https://api.deepl.com"
        var request = try makePOST(URL(string: host + "/v2/translate")!,
                                   body: ["text": [text], "source_lang": "RU", "target_lang": "EN-US"])
        request.setValue("DeepL-Auth-Key " + key, forHTTPHeaderField: "Authorization")
        let object = try await json(request)
        guard let root = object as? [String: Any],
              let translations = root["translations"] as? [[String: Any]],
              let output = translations.first?["text"] as? String else {
            throw EngineError.request("DeepL returned no translation")
        }
        return output
    }

    private static func azure(_ text: String, key: String, region: String) async throws -> String {
        guard !key.isEmpty else { throw EngineError.request("Microsoft key not configured") }
        let url = URL(string: "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&from=ru&to=en")!
        var request = try makePOST(url, body: [["Text": text]])
        request.setValue(key, forHTTPHeaderField: "Ocp-Apim-Subscription-Key")
        if !region.isEmpty {
            request.setValue(region, forHTTPHeaderField: "Ocp-Apim-Subscription-Region")
        }
        let object = try await json(request)
        guard let items = object as? [[String: Any]],
              let translations = items.first?["translations"] as? [[String: Any]],
              let output = translations.first?["text"] as? String else {
            throw EngineError.request("Microsoft returned no translation")
        }
        return output
    }

    private static func google(_ text: String, key: String) async throws -> String {
        guard !key.isEmpty else { throw EngineError.request("Google Cloud key not configured") }
        var components = URLComponents(string: "https://translation.googleapis.com/language/translate/v2")!
        components.queryItems = [URLQueryItem(name: "key", value: key)]
        let request = try makePOST(components.url!, body: [
            "q": text, "source": "ru", "target": "en", "format": "text"
        ])
        let object = try await json(request)
        guard let root = object as? [String: Any],
              let data = root["data"] as? [String: Any],
              let items = data["translations"] as? [[String: Any]],
              let output = items.first?["translatedText"] as? String else {
            throw EngineError.request("Google Cloud returned no translation")
        }
        return output
    }
}


// The view-managed TranslationSession API has been supported since macOS 15.
// Direct TranslationSession(installedSource:) construction is macOS 26+ only.
@available(macOS 15.0, *)
@MainActor
final class AppleTranslationBridge: ObservableObject {
    static let shared = AppleTranslationBridge()
    @Published var configuration: TranslationSession.Configuration?
    private var pending: CheckedContinuation<String, Error>?
    private var pendingText = ""
    private var requestID = UUID()

    private init() {}

    func request(_ text: String) async throws -> String {
        guard pending == nil else {
            throw EngineError.request("Apple is already translating another selection")
        }
        return try await withCheckedThrowingContinuation { continuation in
            let id = UUID()
            requestID = id
            pending = continuation
            pendingText = text
            configuration = TranslationSession.Configuration(
                source: Locale.Language(identifier: "ru"),
                target: Locale.Language(identifier: "en")
            )
            Task { @MainActor in
                try? await Task.sleep(nanoseconds: 12_000_000_000)
                if requestID == id && pending != nil {
                    finish(.failure(EngineError.request("Apple on-device translation timed out")))
                }
            }
        }
    }

    func execute(_ session: TranslationSession) async {
        guard pending != nil else { return }
        do {
            let response = try await session.translate(pendingText)
            finish(.success(response.targetText))
        } catch {
            finish(.failure(error))
        }
    }

    private func finish(_ result: Result<String, Error>) {
        guard let continuation = pending else { return }
        pending = nil
        pendingText = ""
        configuration = nil
        continuation.resume(with: result)
    }
}

@available(macOS 15.0, *)
struct AppleTranslationHost: View {
    @ObservedObject private var bridge = AppleTranslationBridge.shared

    var body: some View {
        Color.clear
            .frame(width: 1, height: 1)
            .translationTask(bridge.configuration) { session in
                await bridge.execute(session)
            }
    }
}
