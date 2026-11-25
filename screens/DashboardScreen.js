import React, { useCallback } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import PrimaryButton from "../components/PrimaryButton";
import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import { useAppContext } from "../context/AppContext";
import { theme } from "../theme";

function ActionCard({ title, subtitle, onPress }) {
  return (
    <Pressable onPress={onPress} style={styles.actionCard}>
      <View style={styles.actionBadge}>
        <Text style={styles.actionBadgeText}>{title.slice(0, 1)}</Text>
      </View>
      <View style={styles.actionCopy}>
        <Text style={styles.actionTitle}>{title}</Text>
        <Text style={styles.actionSubtitle}>{subtitle}</Text>
      </View>
    </Pressable>
  );
}

function isSameCalendarDay(isoOrText) {
  if (!isoOrText) return false;
  const parsed = new Date(isoOrText);
  if (Number.isNaN(parsed.getTime())) return false;
  return parsed.toDateString() === new Date().toDateString();
}

export default function DashboardScreen({ navigation }) {
  const { user, reports, whatsappStatus, logout, refreshReports, refreshWhatsAppStatus } = useAppContext();

  useFocusEffect(
    useCallback(() => {
      refreshReports();
      refreshWhatsAppStatus();
    }, [refreshReports, refreshWhatsAppStatus])
  );

  const todayCount = reports.filter((item) => isSameCalendarDay(item.createdAtIso || item.createdAt)).length;
  const waConnected = Boolean(whatsappStatus?.connected);
  const waOffline = whatsappStatus?.status === "service_error" || whatsappStatus?.status === "gateway_offline";

  const handleLogout = async () => {
    await logout();
    navigation.reset({
      index: 0,
      routes: [{ name: "Login" }],
    });
  };

  return (
    <ScreenContainer>
      <View style={styles.heroCard}>
        <View style={styles.header}>
          <View style={styles.headerCopy}>
            <Text style={styles.greeting}>{user?.organization_name || "Clinical Workspace"}</Text>
            <Text style={styles.name}>{user?.name || "Doctor"}</Text>
            <Text style={styles.specialization}>{user?.specialization || "Healthcare Professional"}</Text>
          </View>
          <PrimaryButton title="Logout" variant="secondary" onPress={handleLogout} />
        </View>

        <View style={styles.metricsRow}>
          <View style={styles.metricCard}>
            <Text style={styles.metricLabel}>Today</Text>
            <Text style={styles.metricValue}>{todayCount}</Text>
            <Text style={styles.metricHelp}>Reports today</Text>
          </View>
          <View style={styles.metricCard}>
            <Text style={styles.metricLabel}>Saved</Text>
            <Text style={styles.metricValue}>{reports.length}</Text>
            <Text style={styles.metricHelp}>Total clinical reports</Text>
          </View>
        </View>
      </View>

      <SectionCard title="WhatsApp Delivery">
        <View style={styles.waRow}>
          <View
            style={[
              styles.waDot,
              waConnected ? styles.waDotOnline : waOffline ? styles.waDotOffline : styles.waDotPending,
            ]}
          />
          <View style={styles.waCopy}>
            <Text style={styles.waTitle}>
              {waConnected
                ? `Connected (${whatsappStatus?.push_name || whatsappStatus?.phone || "Ready"})`
                : waOffline
                  ? "WhatsApp service unavailable"
                  : "WhatsApp not linked"}
            </Text>
            <Text style={styles.waSubtitle}>
              {waConnected
                ? "Patient PDF reports can be sent straight to their WhatsApp."
                : "Scan a WhatsApp Web QR code once to enable instant PDF sharing."}
            </Text>
          </View>
        </View>
        <PrimaryButton
          title={waConnected ? "Manage WhatsApp" : "Connect WhatsApp (Scan QR)"}
          variant={waConnected ? "secondary" : "primary"}
          onPress={() => navigation.navigate("WhatsAppConnect")}
        />
      </SectionCard>

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
          <View style={styles.reportList}>
            {reports.slice(0, 10).map((item) => {
              const title = item.patientName
                ? `${item.patientName}${item.report?.diagnosis ? ` — ${item.report.diagnosis}` : ""}`
                : item.filename || "Consultation Report";

              return (
                <Pressable
                  key={item.reportId || item.id}
                  onPress={() => navigation.navigate("Report", { reportPayload: item })}
                  style={styles.reportRow}
                >
                  <View style={styles.reportMeta}>
                    <Text style={styles.reportTitle}>{title}</Text>
                    <Text style={styles.reportSubtext}>{item.createdAt}</Text>
                  </View>
                  <Text style={styles.reportAction}>Open</Text>
                </Pressable>
              );
            })}
          </View>
        )}
      </SectionCard>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  heroCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing.lg,
    gap: theme.spacing.lg,
    shadowColor: "#000000",
    shadowOpacity: 0.06,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: theme.spacing.md,
  },
  headerCopy: {
    flex: 1,
    gap: 4,
  },
  greeting: {
    color: theme.colors.primary,
    fontWeight: "800",
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: 1,
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
  metricsRow: {
    flexDirection: "row",
    gap: theme.spacing.md,
  },
  metricCard: {
    flex: 1,
    backgroundColor: theme.colors.surfaceMuted,
    borderRadius: theme.radius.md,
    padding: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    gap: 4,
  },
  metricLabel: {
    color: theme.colors.subtext,
    fontSize: 12,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  metricValue: {
    color: theme.colors.text,
    fontSize: 24,
    fontWeight: "800",
  },
  metricHelp: {
    color: theme.colors.subtext,
    fontSize: 13,
  },
  waRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.xs,
  },
  waDot: {
    width: 12,
    height: 12,
    borderRadius: theme.radius.pill,
  },
  waDotOnline: {
    backgroundColor: theme.colors.success,
  },
  waDotPending: {
    backgroundColor: "#D97706",
  },
  waDotOffline: {
    backgroundColor: theme.colors.danger,
  },
  waCopy: {
    flex: 1,
    gap: 2,
  },
  waTitle: {
    color: theme.colors.text,
    fontSize: 15,
    fontWeight: "800",
  },
  waSubtitle: {
    color: theme.colors.subtext,
    fontSize: 13,
    lineHeight: 19,
  },
  actionCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing.md,
    gap: theme.spacing.md,
    flexDirection: "row",
    alignItems: "flex-start",
  },
  actionBadge: {
    width: 44,
    height: 44,
    borderRadius: theme.radius.sm,
    backgroundColor: theme.colors.secondary,
    alignItems: "center",
    justifyContent: "center",
  },
  actionBadgeText: {
    color: theme.colors.primaryDark,
    fontSize: 18,
    fontWeight: "800",
  },
  actionCopy: {
    flex: 1,
    gap: theme.spacing.xxs,
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
  reportList: {
    gap: theme.spacing.sm,
  },
  reportRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.sm,
    padding: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    gap: theme.spacing.sm,
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
