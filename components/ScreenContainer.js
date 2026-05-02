import React from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { ScrollView, StyleSheet, View } from "react-native";

import { theme } from "../theme";

export default function ScreenContainer({
  children,
  scroll = true,
  contentStyle,
  safeEdges,
}) {
  const content = scroll ? (
    <ScrollView
      contentContainerStyle={[styles.scrollContent, contentStyle]}
      showsVerticalScrollIndicator={false}
    >
      <View style={styles.contentShell}>{children}</View>
    </ScrollView>
  ) : (
    <View style={[styles.staticContent, contentStyle]}>
      <View style={styles.contentShell}>{children}</View>
    </View>
  );

  return (
    <SafeAreaView style={styles.safeArea} edges={safeEdges || ["top", "left", "right", "bottom"]}>
      {content}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  scrollContent: {
    flexGrow: 1,
    padding: theme.spacing.lg,
  },
  staticContent: {
    flex: 1,
    padding: theme.spacing.lg,
  },
  contentShell: {
    width: "100%",
    maxWidth: 960,
    alignSelf: "center",
    gap: theme.spacing.lg,
  },
});
