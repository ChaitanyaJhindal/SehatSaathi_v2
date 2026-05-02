import React from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";

import { theme } from "../theme";

export default function PrimaryButton({
  title,
  onPress,
  loading = false,
  variant = "primary",
  disabled = false,
}) {
  const isSecondary = variant === "secondary";
  const buttonDisabled = disabled || loading;

  return (
    <Pressable
      onPress={onPress}
      disabled={buttonDisabled}
      style={[
        styles.button,
        isSecondary ? styles.secondaryButton : styles.primaryButton,
        buttonDisabled && styles.disabledButton,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={isSecondary ? theme.colors.primary : "#FFFFFF"} />
      ) : (
        <Text style={[styles.label, isSecondary ? styles.secondaryLabel : styles.primaryLabel]}>
          {title}
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: 50,
    borderRadius: theme.radius.md,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: theme.spacing.lg,
    borderWidth: 1,
  },
  primaryButton: {
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.primaryDark,
  },
  secondaryButton: {
    backgroundColor: theme.colors.surface,
    borderColor: theme.colors.borderStrong,
  },
  disabledButton: {
    opacity: 0.6,
  },
  label: {
    fontSize: 15,
    fontWeight: "700",
    letterSpacing: 0.3,
  },
  primaryLabel: {
    color: "#FFFFFF",
  },
  secondaryLabel: {
    color: theme.colors.subtext,
  },
});
