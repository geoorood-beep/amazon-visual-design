#include <CoreGraphics/CoreGraphics.h>
#include <ImageIO/ImageIO.h>
#include <CoreFoundation/CoreFoundation.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    size_t width;
    size_t height;
    size_t bytesPerRow;
    unsigned char *pixels;
    CGContextRef context;
} Bitmap;

static Bitmap make_bitmap(size_t width, size_t height) {
    Bitmap b = {0};
    b.width = width;
    b.height = height;
    b.bytesPerRow = width * 4;
    b.pixels = calloc(height, b.bytesPerRow);
    CGColorSpaceRef cs = CGColorSpaceCreateWithName(kCGColorSpaceSRGB);
    b.context = CGBitmapContextCreate(
        b.pixels, width, height, 8, b.bytesPerRow, cs,
        kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big
    );
    CGColorSpaceRelease(cs);
    return b;
}

static void free_bitmap(Bitmap *b) {
    if (b->context) CGContextRelease(b->context);
    free(b->pixels);
    memset(b, 0, sizeof(*b));
}

static CGImageRef load_image(const char *path) {
    CFURLRef url = CFURLCreateFromFileSystemRepresentation(
        NULL, (const UInt8 *)path, (CFIndex)strlen(path), false
    );
    if (!url) return NULL;
    CGImageSourceRef src = CGImageSourceCreateWithURL(url, NULL);
    CFRelease(url);
    if (!src) return NULL;
    CGImageRef image = CGImageSourceCreateImageAtIndex(src, 0, NULL);
    CFRelease(src);
    return image;
}

static double clamp01(double value) {
    if (value < 0.0) return 0.0;
    if (value > 1.0) return 1.0;
    return value;
}

static double smoothstep(double edge0, double edge1, double value) {
    if (edge0 == edge1) return value >= edge1 ? 1.0 : 0.0;
    double t = clamp01((value - edge0) / (edge1 - edge0));
    return t * t * (3.0 - 2.0 * t);
}

// Coordinates are expressed in the final 2508x2508 top-left image space.
static double water_mask(double x, double y, double width, double height) {
    double sx = x * 2508.0 / width;
    double sy = y * 2508.0 / height;

    // Interior water surface: follow the original basin perspective and leave
    // a narrow original-pixel meniscus at every steel contact edge.
    double dx = sx - 1254.0;
    double curvedTop = 1060.0 + 0.000070 * dx * dx;
    double curvedBottom = 1250.0 - 0.000018 * dx * dx;
    double left = 140.0;
    double right = 2368.0;
    double surface = 0.0;
    if (sy >= curvedTop && sy <= curvedBottom && sx >= left && sx <= right) {
        double topFade = smoothstep(curvedTop + 12.0, curvedTop + 30.0, sy);
        double bottomFade = 1.0 - smoothstep(curvedBottom - 30.0, curvedBottom - 12.0, sy);
        double leftCurve = left + 0.00010 * (sy - 1150.0) * (sy - 1150.0);
        double rightCurve = right - 0.00010 * (sy - 1150.0) * (sy - 1150.0);
        double leftFade = smoothstep(leftCurve + 12.0, leftCurve + 34.0, sx);
        double rightFade = 1.0 - smoothstep(rightCurve - 34.0, rightCurve - 12.0, sx);
        surface = fmin(fmin(topFade, bottomFade), fmin(leftFade, rightFade));
    }

    // Falling stream and impact zone; preserve the steel lip at the outlet.
    double streamCenter = 1249.0;
    double streamHalfWidth = 48.0;
    double streamX = 1.0 - smoothstep(streamHalfWidth - 14.0, streamHalfWidth, fabs(sx - streamCenter));
    double streamTop = smoothstep(1055.0, 1072.0, sy);
    double streamBottom = 1.0 - smoothstep(1210.0, 1232.0, sy);
    double stream = streamX * streamTop * streamBottom;

    // Circular impact ripples directly below the stream.
    double ix = (sx - 1249.0) / 260.0;
    double iy = (sy - 1220.0) / 80.0;
    double impactRadius = sqrt(ix * ix + iy * iy);
    double impact = 1.0 - smoothstep(0.72, 0.98, impactRadius);

    return clamp01(fmax(surface * 0.88, fmax(stream, impact * 0.94)));
}

static double seam_sharpen(double sx, double sy, double width, double height) {
    double dx = sx - 1254.0;
    double top = 1060.0 + 0.000070 * dx * dx;
    double bottom = 1250.0 - 0.000018 * dx * dx;
    double topDistance = fabs(sy - top);
    double bottomDistance = fabs(sy - bottom);
    double nearest = fmin(topDistance, bottomDistance);
    double sideDistance = fmin(sx - 140.0, 2368.0 - sx);
    nearest = fmin(nearest, fabs(sideDistance));
    if (nearest > 12.0 || sx < 120.0 || sx > 2388.0 || sy < 1035.0 || sy > 1270.0) return 0.0;
    return (1.0 - smoothstep(6.0, 11.0, nearest)) * 0.26;
}

static unsigned char clamp_u8(double value) {
    if (value < 0.0) return 0;
    if (value > 255.0) return 255;
    return (unsigned char)lrint(value);
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "Usage: %s <original.png> <water_edit.png> <output.png>\n", argv[0]);
        return 2;
    }

    CGImageRef originalImage = load_image(argv[1]);
    CGImageRef editImage = load_image(argv[2]);
    if (!originalImage || !editImage) {
        fprintf(stderr, "Unable to load input image(s)\n");
        if (originalImage) CGImageRelease(originalImage);
        if (editImage) CGImageRelease(editImage);
        return 3;
    }

    size_t width = CGImageGetWidth(originalImage);
    size_t height = CGImageGetHeight(originalImage);
    Bitmap original = make_bitmap(width, height);
    Bitmap edit = make_bitmap(width, height);
    Bitmap output = make_bitmap(width, height);
    if (!original.context || !edit.context || !output.context) {
        fprintf(stderr, "Unable to create bitmap context(s)\n");
        return 4;
    }

    CGContextSetInterpolationQuality(original.context, kCGInterpolationNone);
    CGContextDrawImage(original.context, CGRectMake(0, 0, width, height), originalImage);
    CGContextSetInterpolationQuality(edit.context, kCGInterpolationHigh);
    CGContextDrawImage(edit.context, CGRectMake(0, 0, width, height), editImage);
    memcpy(output.pixels, original.pixels, height * original.bytesPerRow);

    size_t processedWaterPixels = 0;
    for (size_t row = 0; row < height; row++) {
        // Quartz bitmap rows map bottom-to-top; convert to top-left coordinates for the mask.
        double topY = (double)(height - 1 - row);
        for (size_t x = 0; x < width; x++) {
            double alpha = water_mask((double)x, topY, (double)width, (double)height);
            if (alpha <= 0.0001) continue;

            size_t o = row * output.bytesPerRow + x * 4;
            double er = edit.pixels[o];
            double eg = edit.pixels[o + 1];
            double eb = edit.pixels[o + 2];

            // Mild local contrast for transparent stream edges and readable ripples.
            double lum = 0.2126 * er + 0.7152 * eg + 0.0722 * eb;
            double contrast = 1.075;
            er = 128.0 + (er - 128.0) * contrast;
            eg = 128.0 + (eg - 128.0) * contrast;
            eb = 128.0 + (eb - 128.0) * contrast;
            double neutral = (er + eg + eb) / 3.0;
            er += (neutral - er) * 0.04;
            eg += (neutral - eg) * 0.04;
            eb += (neutral - eb) * 0.04;
            if (lum > 205.0) alpha *= 0.94;

            output.pixels[o] = clamp_u8(original.pixels[o] * (1.0 - alpha) + er * alpha);
            output.pixels[o + 1] = clamp_u8(original.pixels[o + 1] * (1.0 - alpha) + eg * alpha);
            output.pixels[o + 2] = clamp_u8(original.pixels[o + 2] * (1.0 - alpha) + eb * alpha);
            output.pixels[o + 3] = original.pixels[o + 3];
            processedWaterPixels++;
        }
    }

    // Locally restore crispness along the existing water/steel contact edge.
    // This uses only source pixels and does not invent a new contour.
    for (size_t row = 1; row + 1 < height; row++) {
        double topY = (double)(height - 1 - row);
        for (size_t x = 1; x + 1 < width; x++) {
            double amount = seam_sharpen((double)x * 2508.0 / (double)width,
                                         topY * 2508.0 / (double)height,
                                         (double)width, (double)height);
            if (amount <= 0.0) continue;
            size_t o = row * output.bytesPerRow + x * 4;
            size_t up = (row - 1) * output.bytesPerRow + x * 4;
            size_t down = (row + 1) * output.bytesPerRow + x * 4;
            size_t left = row * output.bytesPerRow + (x - 1) * 4;
            size_t right = row * output.bytesPerRow + (x + 1) * 4;
            for (int c = 0; c < 3; c++) {
                double center = original.pixels[o + c];
                double neighbors = (original.pixels[up + c] + original.pixels[down + c] +
                                    original.pixels[left + c] + original.pixels[right + c]) * 0.25;
                output.pixels[o + c] = clamp_u8(center + amount * (center - neighbors));
            }
        }
    }

    // Independently compare AFTER all edits, including seam sharpening.
    // The former outside-mask check was unreachable after the early continue
    // and could not demonstrate pixel preservation.
    size_t modified = 0;
    size_t modifiedOutsideWaterMask = 0;
    size_t modifiedOutsideAllowedRegions = 0;
    for (size_t row = 0; row < height; row++) {
        double topY = (double)(height - 1 - row);
        for (size_t x = 0; x < width; x++) {
            size_t o = row * output.bytesPerRow + x * 4;
            if (memcmp(output.pixels + o, original.pixels + o, 4) == 0) continue;
            modified++;
            bool inWater = water_mask((double)x, topY, (double)width, (double)height) > 0.0001;
            bool inSeam = row > 0 && row + 1 < height && x > 0 && x + 1 < width &&
                seam_sharpen((double)x * 2508.0 / (double)width,
                             topY * 2508.0 / (double)height,
                             (double)width, (double)height) > 0.0;
            if (!inWater) modifiedOutsideWaterMask++;
            if (!inWater && !inSeam) modifiedOutsideAllowedRegions++;
        }
    }

    CGImageRef outImage = CGBitmapContextCreateImage(output.context);
    CFURLRef outURL = CFURLCreateFromFileSystemRepresentation(
        NULL, (const UInt8 *)argv[3], (CFIndex)strlen(argv[3]), false
    );
    CGImageDestinationRef destination = CGImageDestinationCreateWithURL(
        outURL, CFSTR("public.png"), 1, NULL
    );
    CGImageDestinationAddImage(destination, outImage, NULL);
    bool ok = CGImageDestinationFinalize(destination);

    printf("PNG export %s; %zux%zu; processed water pixels: %zu; "
           "actual changed pixels: %zu; changed outside water mask: %zu; "
           "changed outside water+seam regions: %zu; "
           "comparison: final in-memory RGBA buffers (reopen disk file for final QA)\n",
           ok ? "succeeded" : "failed", width, height, processedWaterPixels,
           modified, modifiedOutsideWaterMask, modifiedOutsideAllowedRegions);

    if (destination) CFRelease(destination);
    if (outURL) CFRelease(outURL);
    if (outImage) CGImageRelease(outImage);
    CGImageRelease(originalImage);
    CGImageRelease(editImage);
    free_bitmap(&original);
    free_bitmap(&edit);
    free_bitmap(&output);
    return ok ? 0 : 5;
}
