import React, { useEffect } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import ScreenContainer from "../components/ScreenContainer";
import { theme } from "../theme";

export default function SplashScreen({ navigation }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      navigation.replace("Login");
    }, 1800);

    return () => clearTimeout(timer);
  }, [navigation]);

  return (
    <ScreenContainer scroll={false}>
      <View style={styles.container}>
        <View style={styles.logoCard}>
          <Text style={styles.logoGlyph}>+</Text>
        </View>
        <Text style={styles.kicker}>Clinical Assistant</Text>
        <Text style={styles.title}>SehatSaathi</Text>
        <Text style={styles.subtitle}>Voice-first consultation capture and reporting for doctors</Text>
        <ActivityIndicator size="large" color={theme.colors.primary} style={styles.loader} />
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    gap: theme.spacing.md,
  },
  logoCard: {
    width: 96,
    height: 96,
    borderRadius: 28,
    backgroundColor: theme.colors.primary,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#000000",
    shadowOpacity: 0.08,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  },
  logoGlyph: {
    color: "#FFFFFF",
    fontSize: 42,
    fontWeight: "800",
  },
  kicker: {
    color: theme.colors.primary,
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 1.2,
  },
  title: {
    fontSize: 36,
    fontWeight: "800",
    color: theme.colors.text,
  },
  subtitle: {
    fontSize: 16,
    color: theme.colors.subtext,
    textAlign: "center",
    lineHeight: 24,
    maxWidth: 280,
  },
  loader: {
    marginTop: theme.spacing.lg,
  },
});
