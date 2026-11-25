import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import InputField from "../components/InputField";
import PrimaryButton from "../components/PrimaryButton";
import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import { extractErrorMessage, loginDoctor } from "../Services/api";
import { useAppContext } from "../context/AppContext";
import { theme } from "../theme";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginScreen({ navigation }) {
  const { login } = useAppContext();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password.trim()) {
      setError("Please enter both email and password.");
      return;
    }
    if (!EMAIL_RE.test(trimmedEmail)) {
      setError("Please enter a valid email address.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      const doctor = await loginDoctor({
        email: trimmedEmail,
        password,
      });
      await login(doctor);
      navigation.reset({
        index: 0,
        routes: [{ name: "Dashboard" }],
      });
    } catch (loginError) {
      setError(extractErrorMessage(loginError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScreenContainer>
      <View style={styles.hero}>
        <View style={styles.logoRow}>
          <View style={styles.logoBadge}>
            <Text style={styles.logoGlyph}>+</Text>
          </View>
          <View style={styles.logoCopy}>
            <Text style={styles.kicker}>Doctor Console</Text>
            <Text style={styles.title}>Welcome back to SehatSaathi</Text>
          </View>
        </View>
        <Text style={styles.subtitle}>
          Sign in to record consultations, generate reports, and share PDFs via WhatsApp.
        </Text>
      </View>

      <SectionCard title="Login">
        <InputField
          label="Email"
          value={email}
          onChangeText={setEmail}
          placeholder="doctor@hospital.com"
          keyboardType="email-address"
          autoComplete="email"
          returnKeyType="next"
        />
        <InputField
          label="Password"
          value={password}
          onChangeText={setPassword}
          placeholder="Enter password"
          secureTextEntry
          returnKeyType="done"
          onSubmitEditing={handleLogin}
        />
        {!!error && <Text style={styles.error}>{error}</Text>}
        <PrimaryButton title="Login" onPress={handleLogin} loading={loading} />
      </SectionCard>

      <View style={styles.footer}>
        <Text style={styles.footerText}>New to SehatSaathi?</Text>
        <Pressable onPress={() => navigation.navigate("Signup")}>
          <Text style={styles.footerLink}>Create account</Text>
        </Pressable>
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  hero: {
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.xs,
  },
  logoRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: theme.spacing.md,
  },
  logoBadge: {
    width: 56,
    height: 56,
    borderRadius: theme.radius.md,
    backgroundColor: theme.colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  logoGlyph: {
    color: "#FFFFFF",
    fontSize: 28,
    fontWeight: "800",
  },
  logoCopy: {
    flex: 1,
    gap: 4,
  },
  kicker: {
    color: theme.colors.primary,
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  title: {
    color: theme.colors.text,
    fontSize: 30,
    fontWeight: "800",
    lineHeight: 36,
  },
  subtitle: {
    color: theme.colors.subtext,
    fontSize: 15,
    lineHeight: 24,
  },
  error: {
    color: theme.colors.danger,
    fontSize: 14,
    fontWeight: "600",
  },
  footer: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: theme.spacing.xs,
    marginTop: theme.spacing.sm,
  },
  footerText: {
    color: theme.colors.subtext,
  },
  footerLink: {
    color: theme.colors.primary,
    fontWeight: "700",
  },
});
