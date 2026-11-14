import Foundation
import CoreImage
import CoreGraphics
import ImageIO

guard CommandLine.arguments.count == 3 else {
    fputs("Usage: upscale_2x.swift <input.png> <output.png>\n", stderr)
    exit(2)
}

let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])

guard let source = CIImage(contentsOf: inputURL, options: [.applyOrientationProperty: true]) else {
    fputs("Unable to open input image: \(inputURL.path)\n", stderr)
    exit(3)
}

guard let scale = CIFilter(name: "CILanczosScaleTransform") else {
    fputs("CILanczosScaleTransform unavailable\n", stderr)
    exit(4)
}
scale.setValue(source, forKey: kCIInputImageKey)
scale.setValue(2.0, forKey: kCIInputScaleKey)
scale.setValue(1.0, forKey: kCIInputAspectRatioKey)

guard let scaled = scale.outputImage,
      let sharpen = CIFilter(name: "CISharpenLuminance") else {
    fputs("Unable to build upscale pipeline\n", stderr)
    exit(5)
}

// Keep sharpening restrained to avoid halos on fur, gold lettering, and steel edges.
sharpen.setValue(scaled, forKey: kCIInputImageKey)
sharpen.setValue(0.22, forKey: kCIInputSharpnessKey)

guard let finalImage = sharpen.outputImage else {
    fputs("Unable to render sharpened image\n", stderr)
    exit(6)
}

let width = Int((source.extent.width * 2.0).rounded())
let height = Int((source.extent.height * 2.0).rounded())
let outputRect = CGRect(x: 0, y: 0, width: width, height: height)
let cropped = finalImage.cropped(to: outputRect)
let colorSpace = CGColorSpace(name: CGColorSpace.sRGB)!
let context = CIContext(options: [
    .workingColorSpace: colorSpace,
    .outputColorSpace: colorSpace,
    .cacheIntermediates: false
])

do {
    try context.writePNGRepresentation(
        of: cropped,
        to: outputURL,
        format: .RGBA8,
        colorSpace: colorSpace,
        options: [:]
    )
} catch {
    fputs("PNG export failed: \(error)\n", stderr)
    exit(7)
}

print("Wrote \(width)x\(height): \(outputURL.path)")
