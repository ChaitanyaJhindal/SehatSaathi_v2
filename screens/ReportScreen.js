import React, { useState } from "react";
import { Alert, Share, StyleSheet, Text, View } from "react-native";
import * as Linking from "expo-linking";
import * as Sharing from "expo-sharing";

import PrimaryButton from "../components/PrimaryButton";
import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import { downloadPdfToCache } from "../Services/api";
import { theme } from "../theme";

function BulletList({ items }) {
  if (!items?.length) {
    return <Text style={styles.mutedText}>No details available.</Text>;
  }

  return items.map((item, index) => (
    <Text key={`${item}-${index}`} style={styles.bulletItem}>
      {"\u2022"} {item}
    </Text>
  ));
}

export default function ReportScreen({ route }) {
  const reportPayload = route.params?.reportPayload;
  const report = reportPayload?.report || {};
  const [sharing, setSharing] = useState(false);

  const handleViewPdf = async () => {
    if (!reportPayload?.pdfUrl) {
      Alert.alert("PDF unavailable", "No PDF URL was returned by the backend.");
      return;
    }

    const canOpen = await Linking.canOpenURL(reportPayload.pdfUrl);

    if (!canOpen) {
      Alert.alert("Cannot open PDF", "This device cannot open the PDF URL.");
      return;
    }

    await Linking.openURL(reportPayload.pdfUrl);
  };

  const handleSharePdf = async () => {
    if (!reportPayload?.pdfUrl) {
      Alert.alert("PDF unavailable", "No PDF URL was returned by the backend.");
      return;
    }

    try {
      setSharing(true);
      const localUri = await downloadPdfToCache(reportPayload.pdfUrl);
      const canShare = await Sharing.isAvailableAsync();

      if (canShare) {
        await Sharing.shareAsync(localUri);
      } else {
        await Share.share({
          message: reportPayload.pdfUrl,
          url: reportPayload.pdfUrl,
        });
      }
    } catch (error) {
      Alert.alert("Share failed", error.message || "Unable to share the PDF.");
    } finally {
      setSharing(false);
    }
  };

  return (
    <ScreenContainer>
      <SectionCard title="Summary">
        <Text style={styles.summaryTitle}>{reportPayload?.filename || "Consultation Report"}</Text>
        <Text style={styles.summaryMeta}>{reportPayload?.createdAt || "Generated just now"}</Text>
      </SectionCard>

      <SectionCard title="Symptoms">
        <BulletList items={report.symptoms} />
      </SectionCard>

      <SectionCard title="Diagnosis">
        <Text style={styles.bodyText}>{report.diagnosis || "No diagnosis available."}</Text>
      </SectionCard>

      <SectionCard title="Medications">
        <BulletList items={report.medications} />
      </SectionCard>

      <SectionCard title="Dosage">
        <BulletList items={report.dosage} />
      </SectionCard>

      <SectionCard title="Precautions">
        <BulletList items={report.precautions} />
      </SectionCard>

      <SectionCard title="Doctor Notes">
        <Text style={styles.bodyText}>{report.doctor_notes || "No doctor notes available."}</Text>
      </SectionCard>

      <SectionCard title="Transcript" subtle>
        <Text style={styles.bodyText}>{reportPayload?.transcript || "Transcript not provided."}</Text>
      </SectionCard>

      <View style={styles.buttonStack}>
        <PrimaryButton title="View PDF" onPress={handleViewPdf} />
        <PrimaryButton
          title="Share PDF"
          variant="secondary"
          onPress={handleSharePdf}
          loading={sharing}
        />
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  summaryTitle: {
    color: theme.colors.text,
    fontSize: 18,
    fontWeight: "800",
  },
  summaryMeta: {
    color: theme.colors.subtext,
    fontSize: 14,
  },
  bodyText: {
    color: theme.colors.text,
    fontSize: 15,
    lineHeight: 23,
  },
  mutedText: {
    color: theme.colors.subtext,
    fontSize: 15,
  },
  bulletItem: {
    color: theme.colors.text,
    fontSize: 15,
    lineHeight: 23,
  },
  buttonStack: {
    gap: theme.spacing.sm,
    marginTop: theme.spacing.md,
    marginBottom: theme.spacing.lg,
  },
});
