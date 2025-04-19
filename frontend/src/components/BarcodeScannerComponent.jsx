import React, { useEffect } from "react";
import { Html5QrcodeScanner, Html5QrcodeScanType } from "html5-qrcode";

export function BarcodeScannerComponent({ onDetected }) {
  useEffect(() => {
    const scanner = new Html5QrcodeScanner("reader", {
      fps: 15,
      qrbox: 350,
      rememberLastUsedCamera: false,
      supportedScanTypes: [Html5QrcodeScanType.SCAN_TYPE_CAMERA]
    });

    scanner.render(
      (decodedText, decodedResult) => {
        console.log("✅ Barcode detected:", decodedText);
        onDetected(decodedText);
        scanner.clear(); // optionally stop scanning after success
      },
      (errorMessage) => {
        // Suppress noisy 'not found' errors
        if (!errorMessage.includes("No MultiFormat Readers")) {
          console.warn("Scanner error:", errorMessage);
        }
      }
    );

    return () => {
      scanner.clear().catch((e) =>
        console.error("Failed to stop scanner", e)
      );
    };
  }, [onDetected]);

  return (
    <div className="border border-gray-300 p-2 rounded mb-4">
      <div id="reader" className="w-full" />
    </div>
  );
}

