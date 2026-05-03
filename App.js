import "react-native-gesture-handler";
import React from "react";
import { NavigationContainer, DefaultTheme } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { StatusBar } from "expo-status-bar";

import DebugLogPanel from "./components/DebugLogPanel";
import { AppProvider } from "./context/AppContext";
import SplashScreen from "./screens/SplashScreen";
import LoginScreen from "./screens/LoginScreen";
import SignupScreen from "./screens/SignupScreen";
import DashboardScreen from "./screens/DashboardScreen";
import RecordScreen from "./screens/RecordScreen";
import UploadScreen from "./screens/UploadScreen";
import ProcessingScreen from "./screens/ProcessingScreen";
import ReportScreen from "./screens/ReportScreen";
import { theme } from "./theme";

const Stack = createNativeStackNavigator();

const navigationTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: theme.colors.background,
    card: theme.colors.surface,
    text: theme.colors.text,
    border: theme.colors.border,
    primary: theme.colors.primary,
  },
};

export default function App() {
  return (
    <AppProvider>
      <NavigationContainer theme={navigationTheme}>
        <StatusBar style="dark" />
        <Stack.Navigator
          initialRouteName="Splash"
          screenOptions={{
            headerStyle: { backgroundColor: theme.colors.surface },
            headerTintColor: theme.colors.text,
            headerShadowVisible: false,
            contentStyle: { backgroundColor: theme.colors.background },
            animation: "slide_from_right",
          }}
        >
          <Stack.Screen name="Splash" component={SplashScreen} options={{ headerShown: false }} />
          <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
          <Stack.Screen name="Signup" component={SignupScreen} options={{ headerShown: false }} />
          <Stack.Screen name="Dashboard" component={DashboardScreen} options={{ headerShown: false }} />
          <Stack.Screen name="Record" component={RecordScreen} options={{ title: "Record Consultation" }} />
          <Stack.Screen name="Upload" component={UploadScreen} options={{ title: "Upload Audio" }} />
          <Stack.Screen name="Processing" component={ProcessingScreen} options={{ headerShown: false }} />
          <Stack.Screen name="Report" component={ReportScreen} options={{ title: "Clinical Report" }} />
        </Stack.Navigator>
        <DebugLogPanel />
      </NavigationContainer>
    </AppProvider>
  );
}
