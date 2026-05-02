import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { theme } from "../theme";

export default function SectionCard({ title, children, subtle = false }) {
  return (
    <View style={[styles.card, subtle && styles.subtleCard]}>
      <View style={styles.header}>
        <Text style={styles.title}>{title}</Text>
      </View>
      <View style={styles.content}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    shadowColor: "#000000",
    shadowOpacity: 0.06,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
    overflow: "hidden",
  },
  subtleCard: {
    backgroundColor: theme.colors.surfaceMuted,
  },
  header: {
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
    backgroundColor: theme.colors.surfaceMuted,
  },
  title: {
    color: theme.colors.text,
    fontSize: 17,
    fontWeight: "800",
    letterSpacing: 0.2,
  },
  content: {
    gap: theme.spacing.sm,
    padding: theme.spacing.lg,
  },
});
