import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { theme } from "../theme";

export default function SectionCard({ title, children, subtle = false }) {
  return (
    <View style={[styles.card, subtle && styles.subtleCard]}>
      <Text style={styles.title}>{title}</Text>
      <View style={styles.content}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    padding: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    shadowColor: theme.colors.primary,
    shadowOpacity: 0.08,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 3,
  },
  subtleCard: {
    backgroundColor: theme.colors.surfaceMuted,
  },
  title: {
    color: theme.colors.text,
    fontSize: 17,
    fontWeight: "800",
    marginBottom: theme.spacing.sm,
  },
  content: {
    gap: theme.spacing.xs,
  },
});
