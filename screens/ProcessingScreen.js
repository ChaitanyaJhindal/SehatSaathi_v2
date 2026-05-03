import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import { useAppContext } from "../context/AppContext";
import { extractErrorMessage, generateReport } from "../Services/api";
import { theme } from "../theme";

export default function ProcessingScreen({ navigation, route }) {
  const { addReport, logError, logInfo, user } = useAppContext();
  const [error, setError] = useState("");
  const hasStartedRef = useRef(false);
  const audioAsset = route.params?.audioAsset;
  const patientDetails = route.params?.patientDetails || {};
  const sourceLabel = route.params?.sourceLabel || "Consultation audio";

  useEffect(() => {
    if (hasStartedRef.current) {
      return undefined;
    }

    hasStartedRef.current = true;
    let cancelled = false;

    const run = async () => {
      try {
        logInfo("Started report generation", `${sourceLabel}: ${audioAsset?.name || audioAsset?.uri || "unknown file"}`);
        const payload = await generateReport(audioAsset, user, patientDetails);

        if (cancelled) {
          return;
        }

        const reportPayload = {
          id: `${Date.now()}`,
          filename: payload.filename,
          transcript: payload.transcript,
          report: payload.report,
          pdfUrl: payload.pdf_url,
          patientId: payload.patient_id || payload.report?.patient_id,
          patientName: payload.report?.patient_name || patientDetails.name,
          patientAge: payload.report?.age || patientDetails.age,
          patientGender: payload.report?.gender || patientDetails.gender,
          patientPhone: payload.report?.patient_phone || patientDetails.phone,
          createdAt: new Date().toLocaleString(),
        };

        addReport(reportPayload);
        logInfo("Report generation completed", reportPayload.filename || "PDF and report ready");
        navigation.replace("Report", { reportPayload });
      } catch (uploadError) {
        if (!cancelled) {
          setError(extractErrorMessage(uploadError));
          logError("Report generation failed", uploadError);
        }
      }
    };

    run();

    return () => {
      cancelled = true;
    };
  }, [addReport, audioAsset, logError, logInfo, navigation, patientDetails, sourceLabel, user]);

  return (
    <ScreenContainer scroll={false}>
      <View style={styles.wrapper}>
        <SectionCard title="Generating report">
          <View style={styles.loaderWrap}>
            <ActivityIndicator size="large" color={theme.colors.primary} />
          </View>
          <View style={styles.progressLine}>
            <View style={styles.progressFill} />
          </View>
          <Text style={styles.title}>Generating report...</Text>
          <Text style={styles.subtitle}>
            We are uploading {sourceLabel}, transcribing the consultation, and preparing the PDF.
          </Text>
          {!!error && <Text style={styles.error}>{error}</Text>}
          {!!error && (
            <Text style={styles.retry} onPress={() => navigation.goBack()}>
              Go back and try again
            </Text>
          )}
        </SectionCard>
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    flex: 1,
    justifyContent: "center",
  },
  loaderWrap: {
    width: 84,
    height: 84,
    borderRadius: theme.radius.lg,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: theme.colors.surfaceMuted,
    borderWidth: 1,
    borderColor: theme.colors.border,
    alignSelf: "center",
    marginBottom: theme.spacing.md,
  },
  progressLine: {
    height: 8,
    backgroundColor: theme.colors.surfaceHigh,
    borderRadius: theme.radius.pill,
    overflow: "hidden",
  },
  progressFill: {
    width: "62%",
    height: "100%",
    backgroundColor: theme.colors.primary,
  },
  title: {
    color: theme.colors.text,
    fontSize: 24,
    fontWeight: "800",
    textAlign: "center",
  },
  subtitle: {
    color: theme.colors.subtext,
    fontSize: 15,
    lineHeight: 22,
    textAlign: "center",
  },
  error: {
    color: theme.colors.danger,
    fontSize: 14,
    fontWeight: "600",
    textAlign: "center",
    marginTop: theme.spacing.sm,
  },
  retry: {
    color: theme.colors.primary,
    fontSize: 15,
    fontWeight: "700",
    textAlign: "center",
    marginTop: theme.spacing.sm,
  },
});
