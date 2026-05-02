import React from "react";
import { FlatList, Pressable, StyleSheet, Text, View } from "react-native";

import PrimaryButton from "../components/PrimaryButton";
import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import { useAppContext } from "../context/AppContext";
import { theme } from "../theme";

function ActionCard({ title, subtitle, onPress }) {
  return (
    <Pressable onPress={onPress} style={styles.actionCard}>
      <Text style={styles.actionTitle}>{title}</Text>
      <Text style={styles.actionSubtitle}>{subtitle}</Text>
    </Pressable>
  );
}

export default function DashboardScreen({ navigation }) {
  const { user, reports, logout } = useAppContext();

  return (
    <ScreenContainer>
      <View style={styles.header}>
        <View style={styles.headerCopy}>
          <Text style={styles.greeting}>Welcome back</Text>
          <Text style={styles.name}>{user?.name || "Doctor"}</Text>
          <Text style={styles.specialization}>{user?.specialization || "Healthcare Professional"}</Text>
        </View>
        <PrimaryButton title="Logout" variant="secondary" onPress={() => {
          logout();
          navigation.replace("Login");
        }} />
      </View>

      <SectionCard title="Start Consultation">
        <ActionCard
          title="Record Consultation"
          subtitle="Capture live consultation audio with a built-in timer."
          onPress={() => navigation.navigate("Record")}
        />
        <ActionCard
          title="Upload Audio"
          subtitle="Pick an existing audio file and generate a structured report."
          onPress={() => navigation.navigate("Upload")}
        />
      </SectionCard>

      <SectionCard title="Recent Reports" subtle>
        {reports.length === 0 ? (
          <Text style={styles.emptyText}>
            No reports yet. Your generated consultation summaries will appear here.
          </Text>
        ) : (
          <FlatList
            data={reports.slice(0, 5)}
            keyExtractor={(item) => item.id}
            scrollEnabled={false}
            ItemSeparatorComponent={() => <View style={{ height: theme.spacing.sm }} />}
            renderItem={({ item }) => (
              <Pressable
                onPress={() => navigation.navigate("Report", { reportPayload: item })}
                style={styles.reportRow}
              >
                <View style={styles.reportMeta}>
                  <Text style={styles.reportTitle}>{item.filename || "Consultation Report"}</Text>
                  <Text style={styles.reportSubtext}>{item.createdAt}</Text>
                </View>
                <Text style={styles.reportAction}>Open</Text>
              </Pressable>
            )}
          />
        )}
      </SectionCard>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: theme.spacing.md,
    marginBottom: theme.spacing.lg,
  },
  headerCopy: {
    flex: 1,
    gap: 4,
  },
  greeting: {
    color: theme.colors.primary,
    fontWeight: "800",
    fontSize: 14,
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  name: {
    color: theme.colors.text,
    fontSize: 28,
    fontWeight: "800",
  },
  specialization: {
    color: theme.colors.subtext,
    fontSize: 15,
  },
  actionCard: {
    backgroundColor: theme.colors.surfaceMuted,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing.md,
    gap: theme.spacing.xs,
  },
  actionTitle: {
    color: theme.colors.text,
    fontSize: 17,
    fontWeight: "800",
  },
  actionSubtitle: {
    color: theme.colors.subtext,
    fontSize: 14,
    lineHeight: 21,
  },
  emptyText: {
    color: theme.colors.subtext,
    lineHeight: 22,
  },
  reportRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    padding: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  reportMeta: {
    flex: 1,
    gap: 4,
  },
  reportTitle: {
    color: theme.colors.text,
    fontSize: 15,
    fontWeight: "700",
  },
  reportSubtext: {
    color: theme.colors.subtext,
    fontSize: 13,
  },
  reportAction: {
    color: theme.colors.primary,
    fontWeight: "700",
  },
});
