import Foundation
import Vision
import AppKit

let path = CommandLine.arguments[1]
guard let img = NSImage(contentsOfFile: path),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("ERR: cannot load image"); exit(1)
}
let req = VNDetectBarcodesRequest()
if #available(macOS 11.0, *) { req.symbologies = [.qr] }
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
do {
    try handler.perform([req])
    let results = req.results as? [VNBarcodeObservation] ?? []
    if results.isEmpty { print("NO_CODE") }
    for r in results { print("DECODED: \(r.payloadStringValue ?? "<nil>")") }
} catch { print("ERR: \(error)") }
