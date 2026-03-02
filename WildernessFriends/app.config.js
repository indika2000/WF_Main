export default {
  expo: {
    name: "WildernessFriends",
    slug: "wilderness-friends",
    version: "1.0.0",
    orientation: "portrait",
    icon: "./assets/images/icon.png",
    scheme: "wildernessfriends",
    userInterfaceStyle: "automatic",
    newArchEnabled: true,
    ios: {
      supportsTablet: true,
      bundleIdentifier: "com.wildernessfriends.app",
    },
    android: {
      adaptiveIcon: {
        foregroundImage: "./assets/images/adaptive-icon.png",
        backgroundColor: "#1B3A2D",
      },
      package: "com.wildernessfriends.app",
    },
    web: {
      bundler: "metro",
      output: "static",
      favicon: "./assets/images/icon.png",
    },
    plugins: [
      "expo-router",
      [
        "expo-splash-screen",
        {
          image: "./assets/images/splash.png",
          imageWidth: 200,
          resizeMode: "contain",
          backgroundColor: "#1B3A2D",
        },
      ],
      [
        "react-native-vision-camera",
        {
          cameraPermissionText:
            "WildernessFriends needs camera access to scan barcodes and QR codes.",
          enableCodeScanner: true,
        },
      ],
      [
        "expo-build-properties",
        {
          android: {
            kotlinVersion: "2.0.21",
          },
        },
      ],
    ],
    experiments: {
      typedRoutes: true,
    },
    extra: {
      router: {
        origin: false,
      },
      eas: {
        projectId: "97df2d47-8487-45d4-a058-f5990de6677d",
      },
    },
  },
};
