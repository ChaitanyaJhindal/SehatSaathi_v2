import { Alert, Platform } from "react-native";

export function notify(title, message) {
  const text = message ? `${title}: ${message}` : title;
  if (Platform.OS === "web") {
    if (typeof window !== "undefined" && typeof window.alert === "function") {
      window.alert(text);
    }
    return;
  }
  Alert.alert(title, message || "");
}
