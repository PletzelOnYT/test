import AppKit
import SwiftUI
import ScreenCaptureKit
import CoreMedia
import CoreVideo
import CoreImage

/// One-shot user-selected screen/window capture.
/// SCContentSharingPicker grants per-selection capture access on macOS 14+;
/// no system-wide Screen Recording permission or shell subprocess is used.
@available(macOS 14.0, *)
final class PermissionlessScreenPicker: NSObject, SCContentSharingPickerObserver {
    private var stream: SCStream?
    private var output: SingleFrameOutput?
    private var onImage: ((NSImage) -> Void)?
    private var onFailure: ((String) -> Void)?
    private var finished = false

    func begin(onImage: @escaping (NSImage) -> Void, onFailure: @escaping (String) -> Void) {
        guard self.onImage == nil else {
            onFailure("A screen selection is already running.")
            return
        }
        self.onImage = onImage
        self.onFailure = onFailure
        self.finished = false
        let picker = SCContentSharingPicker.shared
        picker.add(self)
        picker.isActive = true
        picker.present()
    }

    func contentSharingPicker(_ picker: SCContentSharingPicker,
                              didUpdateWith filter: SCContentFilter,
                              for stream: SCStream?) {
        Task { @MainActor in
            await self.capture(filter)
        }
    }

    func contentSharingPicker(_ picker: SCContentSharingPicker, didCancelFor stream: SCStream?) {
        finish(.failure(CaptureError("Selection cancelled.")))
    }

    func contentSharingPickerStartDidFailWithError(_ error: Error) {
        finish(.failure(CaptureError("The macOS picker couldn't open: " + error.localizedDescription)))
    }

    @MainActor
    private func capture(_ filter: SCContentFilter) async {
        guard !finished else { return }
        do {
            let config = SCStreamConfiguration()
            let rect = filter.contentRect
            let pixelScale = filter.pointPixelScale
            config.width = max(256, Int(rect.width * pixelScale))
            config.height = max(256, Int(rect.height * pixelScale))
            config.minimumFrameInterval = CMTime(value: 1, timescale: 30)
            config.queueDepth = 3
            config.showsCursor = false
            config.capturesAudio = false
            config.pixelFormat = kCVPixelFormatType_32BGRA

            let output = SingleFrameOutput { [weak self] image in
                self?.finish(.success(image))
            }
            self.output = output
            let active = SCStream(filter: filter, configuration: config, delegate: nil)
            self.stream = active
            try active.addStreamOutput(output, type: .screen,
                                       sampleHandlerQueue: DispatchQueue(label: "app.russiansnip.frame", qos: .userInitiated))
            try await active.startCapture()
            Task { @MainActor in
                try? await Task.sleep(nanoseconds: 8_000_000_000)
                if !self.finished {
                    self.finish(.failure(CaptureError("Screen selection timed out. Use Paste Screenshot instead.")))
                }
            }
        } catch {
            finish(.failure(CaptureError("Cannot capture selected content: " + error.localizedDescription)))
        }
    }

    private func finish(_ result: Result<NSImage, CaptureError>) {
        DispatchQueue.main.async { [weak self] in
            guard let self, !self.finished else { return }
            self.finished = true
            SCContentSharingPicker.shared.remove(self)
            if let active = self.stream {
                Task { try? await active.stopCapture() }
            }
            self.stream = nil
            self.output = nil
            let success = self.onImage
            let failure = self.onFailure
            self.onImage = nil
            self.onFailure = nil
            switch result {
            case .success(let image):
                success?(image)
            case .failure(let error):
                failure?(error.message)
            }
        }
    }
}

struct CaptureError: Error {
    let message: String
    init(_ message: String) { self.message = message }
}

@available(macOS 14.0, *)
private final class SingleFrameOutput: NSObject, SCStreamOutput {
    private let lock = NSLock()
    private var completed = false
    private let completion: (NSImage) -> Void
    private let context = CIContext()

    init(completion: @escaping (NSImage) -> Void) {
        self.completion = completion
    }

    func stream(_ stream: SCStream,
                didOutputSampleBuffer sampleBuffer: CMSampleBuffer,
                of outputType: SCStreamOutputType) {
        guard outputType == .screen, sampleBuffer.isValid,
              let pixels = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        lock.lock()
        let shouldProcess = !completed
        if shouldProcess { completed = true }
        lock.unlock()
        guard shouldProcess else { return }
        let ciImage = CIImage(cvPixelBuffer: pixels)
        guard let image = context.createCGImage(ciImage, from: ciImage.extent) else { return }
        completion(NSImage(cgImage: image, size: NSSize(width: image.width, height: image.height)))
    }
}

/// Interactive crop, operating purely on pixels already obtained from
/// a user-approved system picker or clipboard image.
struct ScreenshotCropSheet: View {
    let image: NSImage
    let accept: (NSImage) -> Void
    let cancel: () -> Void

    @State private var start: CGPoint?
    @State private var end: CGPoint?

    var body: some View {
        VStack(spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Select Russian text").font(.title2).bold()
                    Text("Drag across the part you want translated, then choose Crop & Translate.")
                        .font(.callout).foregroundStyle(.secondary)
                }
                Spacer()
                Button("Cancel") { cancel() }
                Button("Use Full Image") { accept(image) }
                Button("Crop & Translate") { crop() }
                    .buttonStyle(.borderedProminent)
                    .disabled(start == nil || end == nil)
            }
            GeometryReader { geometry in
                let original = image.size
                let canvas = geometry.size
                let factor = min(canvas.width / max(original.width, 1),
                                 canvas.height / max(original.height, 1))
                let shown = CGSize(width: original.width * factor, height: original.height * factor)
                ZStack {
                    Color.black.opacity(0.88)
                    Image(nsImage: image)
                        .resizable()
                        .frame(width: shown.width, height: shown.height)
                        .overlay(alignment: .topLeading) {
                            if let start, let end {
                                let rect = bounds(start, end)
                                Rectangle()
                                    .fill(Color.accentColor.opacity(0.15))
                                    .overlay(Rectangle().stroke(.white, lineWidth: 2))
                                    .frame(width: rect.width, height: rect.height)
                                    .position(x: rect.midX, y: rect.midY)
                            }
                        }
                        .gesture(
                            DragGesture(minimumDistance: 2)
                                .onChanged { value in
                                    if start == nil { start = value.startLocation }
                                    end = value.location
                                }
                                .onEnded { value in end = value.location }
                        )
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(.black)
                .onChange(of: image) { _ in start = nil; end = nil }
            }
            .clipShape(RoundedRectangle(cornerRadius: 9))
        }
        .padding(16)
        .frame(width: 910, height: 650)
    }

    private func bounds(_ a: CGPoint, _ b: CGPoint) -> CGRect {
        CGRect(x: min(a.x, b.x), y: min(a.y, b.y),
               width: abs(a.x - b.x), height: abs(a.y - b.y))
    }

    private func crop() {
        guard let start, let end,
              let tiff = image.tiffRepresentation,
              let bitmap = NSBitmapImageRep(data: tiff),
              let original = bitmap.cgImage else { return }

        let availableWidth: CGFloat = 878
        let availableHeight: CGFloat = 560
        let scale = min(availableWidth / max(image.size.width, 1),
                        availableHeight / max(image.size.height, 1))
        let displayedWidth = image.size.width * scale
        let displayedHeight = image.size.height * scale
        let selected = bounds(start, end)

        let pixelX = selected.minX / displayedWidth * CGFloat(original.width)
        let pixelY = selected.minY / displayedHeight * CGFloat(original.height)
        let pixelW = selected.width / displayedWidth * CGFloat(original.width)
        let pixelH = selected.height / displayedHeight * CGFloat(original.height)
        let rectangle = CGRect(x: max(0, pixelX), y: max(0, pixelY),
                               width: min(CGFloat(original.width) - max(0, pixelX), pixelW),
                               height: min(CGFloat(original.height) - max(0, pixelY), pixelH))
        guard rectangle.width >= 8, rectangle.height >= 8,
              let cropped = original.cropping(to: rectangle) else { return }
        accept(NSImage(cgImage: cropped,
                       size: NSSize(width: cropped.width, height: cropped.height)))
    }
}
