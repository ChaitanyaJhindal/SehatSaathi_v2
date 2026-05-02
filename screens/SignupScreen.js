import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import InputField from "../components/InputField";
import PrimaryButton from "../components/PrimaryButton";
import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import { useAppContext } from "../context/AppContext";
import { theme } from "../theme";

export default function SignupScreen({ navigation }) {
  const { login } = useAppContext();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    specialization: "",
  });
  const [error, setError] = useState("");

  const updateField = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const handleSignup = () => {
    const hasEmptyField = Object.values(form).some((value) => !value.trim());

    if (hasEmptyField) {
      setError("Please complete all signup fields.");
      return;
    }

    login({
      name: form.name.trim(),
      email: form.email.trim(),
      specialization: form.specialization.trim(),
    });
    navigation.replace("Dashboard");
  };

  return (
    <ScreenContainer>
      <View style={styles.hero}>
        <Text style={styles.kicker}>Create Account</Text>
        <Text style={styles.title}>Set up your doctor workspace</Text>
        <Text style={styles.subtitle}>
          This demo uses local auth state so you can test the full report flow right away.
        </Text>
      </View>

      <SectionCard title="Doctor Details">
        <InputField
          label="Full Name"
          value={form.name}
          onChangeText={(value) => updateField("name", value)}
          placeholder="Dr. Meera Sharma"
          autoCapitalize="words"
        />
        <InputField
          label="Email"
          value={form.email}
          onChangeText={(value) => updateField("email", value)}
          placeholder="doctor@hospital.com"
          keyboardType="email-address"
        />
        <InputField
          label="Password"
          value={form.password}
          onChangeText={(value) => updateField("password", value)}
          placeholder="Create a password"
          secureTextEntry
        />
        <InputField
          label="Specialization"
          value={form.specialization}
          onChangeText={(value) => updateField("specialization", value)}
          placeholder="Cardiology"
          autoCapitalize="words"
        />
        {!!error && <Text style={styles.error}>{error}</Text>}
        <PrimaryButton title="Create Account" onPress={handleSignup} />
      </SectionCard>

      <View style={styles.footer}>
        <Text style={styles.footerText}>Already have an account?</Text>
        <Pressable onPress={() => navigation.goBack()}>
          <Text style={styles.footerLink}>Login</Text>
        </Pressable>
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  hero: {
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.lg,
  },
  kicker: {
    color: theme.colors.primary,
    fontSize: 14,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  title: {
    color: theme.colors.text,
    fontSize: 30,
    fontWeight: "800",
    lineHeight: 36,
  },
  subtitle: {
    color: theme.colors.subtext,
    fontSize: 16,
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
    marginTop: theme.spacing.lg,
  },
  footerText: {
    color: theme.colors.subtext,
  },
  footerLink: {
    color: theme.colors.primary,
    fontWeight: "700",
  },
});
