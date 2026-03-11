import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  Modal,
  TouchableOpacity,
  ImageBackground,
  StyleSheet,
  Dimensions,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import {
  Camera,
  useCameraDevice,
  useCameraPermission,
  useCodeScanner,
} from "react-native-vision-camera";

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get("window");
const MODAL_WIDTH = SCREEN_WIDTH * 0.85;
const MODAL_HEIGHT = SCREEN_HEIGHT * 0.55;
const CAMERA_HEIGHT = 150; // Tight around crosshairs + text

// All linear barcode types normalize to EAN_13 for consistent deduplication.
// UPC-A is a subset of EAN-13 (12 vs 13 digits) — the backend normalises
// UPC-A values to EAN-13 by prepending "0", so they must share a code_type.
const CAMERA_TYPE_MAP: Record<string, string> = {
  "ean-13": "EAN_13",
  "ean-8": "EAN_13",
  "upc-a": "EAN_13",
  "upc-e": "EAN_13",
  qr: "QR",
  "code-128": "EAN_13",
  "code-39": "EAN_13",
  "code-93": "EAN_13",
};

interface CreationCameraModalProps {
  visible: boolean;
  onClose: () => void;
  onCodeScanned: (codeType: string, rawValue: string) => void;
}

export default function CreationCameraModal({
  visible,
  onClose,
  onCodeScanned,
}: CreationCameraModalProps) {
  const { hasPermission, requestPermission } = useCameraPermission();
  const device = useCameraDevice("back");
  const [hasScanned, setHasScanned] = useState(false);

  const codeScanner = useCodeScanner({
    codeTypes: ["qr", "ean-13", "ean-8", "upc-a", "upc-e", "code-128"],
    onCodeScanned: (codes) => {
      if (hasScanned) return;
      if (codes.length > 0 && codes[0].value) {
        setHasScanned(true);
        const scannedType = codes[0].type;
        const scannedValue = codes[0].value;
        const mappedType = CAMERA_TYPE_MAP[scannedType] || "EAN_13";
        onCodeScanned(mappedType, scannedValue);
      }
    },
  });

  const handleClose = useCallback(() => {
    setHasScanned(false);
    onClose();
  }, [onClose]);

  const handleShow = useCallback(() => {
    setHasScanned(false);
  }, []);

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={handleClose}
      onShow={handleShow}
    >
      <View style={styles.container}>
        {/* Full-screen backdrop — tap to close */}
        <TouchableOpacity
          style={styles.backdrop}
          activeOpacity={1}
          onPress={handleClose}
        />

        {/* Centered frame panel */}
        <ImageBackground
          source={require("../assets/images/character_creator/Character_Creator_Frame.png")}
          style={styles.frameContainer}
          resizeMode="stretch"
        >
          {/* Camera viewport — tight around crosshairs */}
          <View style={styles.cameraArea}>
            {!hasPermission ? (
              <View style={styles.permissionView}>
                <Ionicons name="camera-outline" size={36} color="#9A8D82" />
                <Text style={styles.permissionTitle}>Camera Access</Text>
                <TouchableOpacity
                  style={styles.permissionButton}
                  onPress={requestPermission}
                >
                  <Text style={styles.permissionButtonText}>Grant Permission</Text>
                </TouchableOpacity>
              </View>
            ) : !device ? (
              <View style={styles.permissionView}>
                <Ionicons name="warning-outline" size={36} color="#C45A4A" />
                <Text style={styles.permissionTitle}>No Camera Found</Text>
              </View>
            ) : (
              <View style={styles.cameraContainer}>
                <Camera
                  style={StyleSheet.absoluteFill}
                  device={device}
                  isActive={visible && !hasScanned}
                  codeScanner={codeScanner}
                />
                {/* Crosshair guides */}
                <View style={scanStyles.overlay}>
                  <View style={scanStyles.frame}>
                    <View style={[scanStyles.corner, scanStyles.topLeft]} />
                    <View style={[scanStyles.corner, scanStyles.topRight]} />
                    <View style={[scanStyles.corner, scanStyles.bottomLeft]} />
                    <View style={[scanStyles.corner, scanStyles.bottomRight]} />
                  </View>
                  <Text style={styles.instructionText}>
                    Point at a barcode or QR code
                  </Text>
                </View>
              </View>
            )}
          </View>

          {/* Tap to close hint inside frame */}
          <View style={styles.hintRow}>
            <Ionicons name="close-circle-outline" size={16} color="rgba(100,80,60,0.5)" />
            <Text style={styles.hintText}>Tap outside to close</Text>
          </View>
        </ImageBackground>
      </View>
    </Modal>
  );
}

const CORNER_SIZE = 24;
const CORNER_WIDTH = 3;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(0, 0, 0, 0.6)",
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
  },
  frameContainer: {
    height: MODAL_HEIGHT,
    width: MODAL_WIDTH,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingTop: 40,
    paddingBottom: 16,
  },
  cameraArea: {
    width: "100%",
    height: CAMERA_HEIGHT,
    borderRadius: 12,
    overflow: "hidden",
    backgroundColor: "#1A1A1A",
  },
  cameraContainer: {
    flex: 1,
  },
  permissionView: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 20,
    backgroundColor: "#FAF7F2",
  },
  permissionTitle: {
    color: "#3B2F2F",
    fontSize: 16,
    fontWeight: "bold",
    marginTop: 8,
    textAlign: "center",
  },
  permissionButton: {
    backgroundColor: "#7B8F6B",
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 10,
    marginTop: 12,
  },
  permissionButtonText: {
    color: "#fff",
    fontSize: 13,
    fontWeight: "600",
  },
  instructionText: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "600",
    marginTop: 10,
    textShadowColor: "rgba(0,0,0,0.8)",
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 4,
  },
  hintRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 12,
    gap: 6,
  },
  hintText: {
    color: "rgba(100,80,60,0.5)",
    fontSize: 11,
  },
});

const scanStyles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: "center",
    alignItems: "center",
  },
  frame: {
    width: 180,
    height: 100,
  },
  corner: {
    position: "absolute",
    width: CORNER_SIZE,
    height: CORNER_SIZE,
  },
  topLeft: {
    top: 0,
    left: 0,
    borderTopWidth: CORNER_WIDTH,
    borderLeftWidth: CORNER_WIDTH,
    borderColor: "#7B8F6B",
    borderTopLeftRadius: 4,
  },
  topRight: {
    top: 0,
    right: 0,
    borderTopWidth: CORNER_WIDTH,
    borderRightWidth: CORNER_WIDTH,
    borderColor: "#7B8F6B",
    borderTopRightRadius: 4,
  },
  bottomLeft: {
    bottom: 0,
    left: 0,
    borderBottomWidth: CORNER_WIDTH,
    borderLeftWidth: CORNER_WIDTH,
    borderColor: "#7B8F6B",
    borderBottomLeftRadius: 4,
  },
  bottomRight: {
    bottom: 0,
    right: 0,
    borderBottomWidth: CORNER_WIDTH,
    borderRightWidth: CORNER_WIDTH,
    borderColor: "#7B8F6B",
    borderBottomRightRadius: 4,
  },
});
