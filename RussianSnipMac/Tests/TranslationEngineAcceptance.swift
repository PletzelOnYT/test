import Foundation

@main
struct TranslationEngineAcceptanceTests {
    static func check(_ condition: Bool, _ message: String) {
        if !condition {
            fputs("FAILED: " + message + "\n", stderr)
            exit(1)
        }
    }

    static func main() {
        let russian = String(repeating: "Привет, мир! Как дела? ", count: 100)
        let pieces = SmartTranslate.chunk(russian, limit: 430)
        check(pieces.count > 3, "long Russian content must split")
        check(pieces.joined() == russian, "chunking must preserve every source character")
        check(pieces.allSatisfy { $0.utf8.count <= 430 }, "MyMemory q must stay under 500 UTF-8 bytes")
        let sample = "Through a hundred years a girl will live in Moscow."
        check((try? SmartTranslate.validate(sample, source: "Через сто лет будет жить девочка.")) == sample,
              "legitimate English output must pass")
        check((try? SmartTranslate.validate("Привет мир", source: "Привет мир")) == nil,
              "untranslated Cyrillic must be rejected")
        check((try? SmartTranslate.validate("<html>bad gateway</html>", source: "Привет")) == nil,
              "HTML error page must be rejected")
        let defaults = EngineSettings()
        let options = SmartTranslate.available(defaults)
        check(options.contains(.myMemory), "no-key MyMemory fallback must be present")
        check(options.contains(.apple), "Apple on-device fallback must be present")
        check(options.count >= 6, "several no-key fallbacks should be available")
        var settings = defaults
        settings.allowCommunity = false
        check(SmartTranslate.available(settings).count == 2,
              "community providers must be removable in privacy mode")
        settings.deeplKey = "example:fx"
        settings.azureKey = "sample"
        settings.googleKey = "sample"
        settings.libreURL = "https://private.example.org"
        check(SmartTranslate.available(settings).count == 6,
              "all four configured official/custom providers should appear")
        print("PASS: Unicode chunking, language guards, HTML rejection, fallback ordering, privacy toggle")
    }
}
