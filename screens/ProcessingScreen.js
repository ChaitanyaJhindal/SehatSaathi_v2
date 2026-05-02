import React, { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import { useAppContext } from "../context/AppContext";
import { extractErrorMessage, generateReport } from "../Services/api";
import { theme } from "../theme";

export default function ProcessingScreen({ navigation, route }) {
  const { addReport } = useAppContext();
  const [error, setError] = useState("");
  const audioAsset = route.params?.audioAsset;
  const sourceLabel = route.params?.sourceLabel || "Consultation audio";

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        const payload = await generateReport(audioAsset);

        if (cancelled) {
          return;
        }

        const reportPayload = {
          id: `${Date.now()}`,
          filename: payload.filename,
          transcript: payload.transcript,
          report: payload.report,
          pdfUrl: payload.pdf_url,
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
  }, [addReport, audioAsset, navigation]);

  return (
    <ScreenContainer scroll={false}>
      <View style={styles.wrapper}>
        <SectionCard title="Generating report">
          <View style={styles.loaderWrap}>
            <ActivityIndicator size="large" color={theme.colors.primary} />
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
    borderRadius: 28,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: theme.colors.secondary,
    alignSelf: "center",
    marginBottom: theme.spacing.md,
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
