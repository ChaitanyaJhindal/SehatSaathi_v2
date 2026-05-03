import React, { useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { useAppContext } from "../context/AppContext";
import { theme } from "../theme";

function getLevelStyle(level) {
  return level === "error" ? styles.errorPill : styles.infoPill;
}

export default function DebugLogPanel() {
  const { logs, clearLogs } = useAppContext();
  const [expanded, setExpanded] = useState(false);

  const recentLogs = useMemo(() => logs.slice(0, 8), [logs]);

  return (
    <View pointerEvents="box-none" style={styles.overlay}>
      <Pressable style={styles.toggle} onPress={() => setExpanded((current) => !current)}>
        <Text style={styles.toggleText}>Logs ({logs.length})</Text>
      </Pressable>

      {expanded && (
        <View style={styles.panel}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Mobile Debug Logs</Text>
            <Pressable onPress={clearLogs}>
              <Text style={styles.clearText}>Clear</Text>
            </Pressable>
          </View>

          {!recentLogs.length ? (
            <Text style={styles.emptyText}>No logs yet.</Text>
          ) : (
            <ScrollView style={styles.logList} contentContainerStyle={styles.logListContent}>
              {recentLogs.map((entry) => (
                <View key={entry.id} style={styles.logCard}>
                  <View style={styles.logHeader}>
                    <View style={[styles.levelPill, getLevelStyle(entry.level)]}>
                      <Text style={styles.levelText}>{entry.level.toUpperCase()}</Text>
                    </View>
                    <Text style={styles.timeText}>{entry.createdAt}</Text>
                  </View>
                  <Text style={styles.messageText}>{entry.message}</Text>
                  {!!entry.details && <Text style={styles.detailsText}>{entry.details}</Text>}
                </View>
              ))}
            </ScrollView>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    position: "absolute",
    left: theme.spacing.sm,
    right: theme.spacing.sm,
    bottom: theme.spacing.lg,
    alignItems: "flex-end",
  },
  toggle: {
    backgroundColor: theme.colors.text,
    borderRadius: theme.radius.pill,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.xs,
    shadowColor: "#000",
    shadowOpacity: 0.12,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  toggleText: {
    color: theme.colors.surface,
    fontSize: 13,
    fontWeight: "800",
  },
  panel: {
    marginTop: theme.spacing.sm,
    width: "100%",
    maxHeight: 280,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing.md,
    shadowColor: "#000",
    shadowOpacity: 0.1,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 6,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: theme.spacing.sm,
  },
  headerTitle: {
    color: theme.colors.text,
    fontSize: 15,
    fontWeight: "800",
  },
  clearText: {
    color: theme.colors.primary,
    fontSize: 14,
    fontWeight: "700",
  },
  emptyText: {
    color: theme.colors.subtext,
    fontSize: 14,
  },
  logList: {
    maxHeight: 210,
  },
  logListContent: {
    gap: theme.spacing.sm,
  },
  logCard: {
    backgroundColor: theme.colors.surfaceMuted,
    borderRadius: theme.radius.md,
    padding: theme.spacing.sm,
    borderWidth: 1,
    borderColor: theme.colors.border,
    gap: 6,
  },
  logHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  levelPill: {
    borderRadius: theme.radius.pill,
    paddingHorizontal: theme.spacing.xs,
    paddingVertical: 4,
  },
  infoPill: {
    backgroundColor: theme.colors.secondary,
  },
  errorPill: {
    backgroundColor: "#F9DEDC",
  },
  levelText: {
    color: theme.colors.text,
    fontSize: 11,
    fontWeight: "800",
  },
  timeText: {
    color: theme.colors.subtext,
    fontSize: 11,
  },
  messageText: {
    color: theme.colors.text,
    fontSize: 14,
    fontWeight: "700",
  },
  detailsText: {
    color: theme.colors.subtext,
    fontSize: 12,
    lineHeight: 18,
  },
});
