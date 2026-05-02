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
          <Text style={styles.logoGlyph}>S</Text>
        </View>
        <Text style={styles.title}>SehatSaathi</Text>
        <Text style={styles.subtitle}>Voice-first clinical reporting for doctors</Text>
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
    width: 110,
    height: 110,
    borderRadius: 32,
    backgroundColor: theme.colors.primary,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: theme.colors.primary,
    shadowOpacity: 0.18,
    shadowRadius: 22,
    shadowOffset: { width: 0, height: 12 },
    elevation: 6,
  },
  logoGlyph: {
    color: "#FFFFFF",
    fontSize: 52,
    fontWeight: "800",
  },
  title: {
    fontSize: 34,
    fontWeight: "800",
    color: theme.colors.text,
  },
  subtitle: {
    fontSize: 16,
    color: theme.colors.subtext,
    textAlign: "center",
    paddingHorizontal: theme.spacing.xl,
  },
  loader: {
    marginTop: theme.spacing.lg,
  },
});
