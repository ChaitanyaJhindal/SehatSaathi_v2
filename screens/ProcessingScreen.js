import React, { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import PrimaryButton from "../components/PrimaryButton";
import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import { useAppContext } from "../context/AppContext";
import { extractErrorMessage, generateReport } from "../Services/api";
import { theme } from "../theme";

export default function ProcessingScreen({ navigation, route }) {
  const { addReport, user } = useAppContext();
  const [error, setError] = useState("");
  const [runNonce, setRunNonce] = useState(0);
  const audioAsset = route.params?.audioAsset;
  const patientDetails = route.params?.patientDetails || {};
  const sourceLabel = route.params?.sourceLabel || "Consultation audio";

  useEffect(() => {
    if (!audioAsset) {
      setError("No audio file was provided. Please go back and record or select an audio file.");
      return undefined;
    }

    let cancelled = false;
    setError("");

    const run = async () => {
      try {
        const payload = await generateReport(audioAsset, user, patientDetails);

        if (cancelled) {
          return;
        }

        const ageVal =
          payload.report?.patient_age ??
          payload.report?.age ??
          (patientDetails.age !== "" ? patientDetails.age : null);

        const reportPayload = {
          id: payload.report_id || payload.report?.report_id || `${Date.now()}`,
          filename: payload.filename || sourceLabel,
          transcript: payload.transcript || "",
          report: payload.report || {},
          pdfUrl: payload.pdf_url,
          reportId: payload.report_id || payload.report?.report_id,
          reportRecordId: payload.report_record_id,
          patientId: payload.patient_id || payload.report?.patient_id,
          patientName: payload.report?.patient_name || patientDetails.name,
          patientAge: ageVal,
          patientGender: payload.report?.patient_gender ?? payload.report?.gender ?? patientDetails.gender,
          patientPhone:
            payload.report?.patient_phone ?? payload.report?.patient_mobile ?? patientDetails.phone,
          patientNotes: payload.report?.patient_notes ?? patientDetails.notes,
          doctorName: payload.report?.doctor_name || user?.name,
          createdAtIso: new Date().toISOString(),
          createdAt: new Date().toLocaleString(),
        };

        addReport(reportPayload);
        navigation.replace("Report", { reportPayload });
      } catch (uploadError) {
        if (!cancelled) {
          setError(extractErrorMessage(uploadError));
        }
      }
    };

    run();

    return () => {
      cancelled = true;
    };
  }, [runNonce]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleGoBack = () => {
    if (navigation.canGoBack()) {
      navigation.goBack();
    } else {
      navigation.replace("Dashboard");
    }
  };

  return (
    <ScreenContainer scroll={false}>
      <View style={styles.wrapper}>
        <SectionCard title={error ? "Report Generation Failed" : "Generating Report"}>
          {!error ? (
            <>
              <View style={styles.loaderWrap}>
                <ActivityIndicator size="large" color={theme.colors.primary} />
              </View>
              <View style={styles.progressLine}>
                <View style={styles.progressFill} />
              </View>
              <Text style={styles.title}>Generating report...</Text>
              <Text style={styles.subtitle}>
                Uploading {sourceLabel}, transcribing the consultation, extracting clinical fields, and building the PDF.
              </Text>
            </>
          ) : (
            <>
              <Text style={styles.error}>{error}</Text>
              <View style={styles.buttonStack}>
                {!!audioAsset && (
                  <PrimaryButton
                    title="Retry"
                    onPress={() => setRunNonce((n) => n + 1)}
                  />
                )}
                <PrimaryButton
                  title="Back to Form"
                  variant="secondary"
                  onPress={handleGoBack}
                />
              </View>
            </>
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
    width: "68%",
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
    fontSize: 15,
    fontWeight: "600",
    textAlign: "center",
    marginVertical: theme.spacing.sm,
  },
  buttonStack: {
    gap: theme.spacing.sm,
    marginTop: theme.spacing.sm,
  },
});
