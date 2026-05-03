import React, { useState } from "react";
import { Alert, Share, StyleSheet, Text, TextInput, View } from "react-native";
import * as Linking from "expo-linking";
import * as Sharing from "expo-sharing";

import PrimaryButton from "../components/PrimaryButton";
import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import { useAppContext } from "../context/AppContext";
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

function toEditableList(items) {
  return Array.isArray(items) ? items.join("\n") : "";
}

function toListItems(value) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function ReportScreen({ route }) {
  const { logError, logInfo } = useAppContext();
  const reportPayload = route.params?.reportPayload;
  const report = reportPayload?.report || {};
  const [sharing, setSharing] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editableReport, setEditableReport] = useState(() => ({
    symptoms: toEditableList(report.symptoms),
    diagnosis: report.diagnosis || "",
    medications: toEditableList(report.medications),
    dosage: toEditableList(report.dosage),
    precautions: toEditableList(report.precautions),
    doctor_notes: report.doctor_notes || "",
  }));

  const displayReport = {
    symptoms: toListItems(editableReport.symptoms),
    diagnosis: editableReport.diagnosis.trim(),
    medications: toListItems(editableReport.medications),
    dosage: toListItems(editableReport.dosage),
    precautions: toListItems(editableReport.precautions),
    doctor_notes: editableReport.doctor_notes.trim(),
  };

  const updateField = (field, value) => {
    setEditableReport((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const toggleEditing = () => {
    if (editing) {
      logInfo("Clinical report edited manually");
    }

    setEditing((current) => !current);
  };

  const handleViewPdf = async () => {
    if (!reportPayload?.pdfUrl) {
      Alert.alert("PDF unavailable", "No PDF URL was returned by the backend.");
      return;
    }

    const canOpen = await Linking.canOpenURL(reportPayload.pdfUrl);

    if (!canOpen) {
      logError("PDF open check failed", "Linking cannot open the generated PDF URL.");
      Alert.alert("Cannot open PDF", "This device cannot open the PDF URL.");
      return;
    }

    logInfo("Opening PDF URL", reportPayload.pdfUrl);
    await Linking.openURL(reportPayload.pdfUrl);
  };

  const handleSharePdf = async () => {
    if (!reportPayload?.pdfUrl) {
      Alert.alert("PDF unavailable", "No PDF URL was returned by the backend.");
      return;
    }

    try {
      setSharing(true);
      logInfo("Started PDF share flow", reportPayload.pdfUrl);
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
      logError("Share PDF failed", error);
      Alert.alert("Share failed", error.message || "Unable to share the PDF.");
    } finally {
      setSharing(false);
    }
  };

  return (
    <ScreenContainer>
      <SectionCard title="Summary">
        <View style={styles.summaryHeader}>
          <View style={styles.summaryCopy}>
            <Text style={styles.summaryTitle}>{reportPayload?.filename || "Consultation Report"}</Text>
            <Text style={styles.summaryMeta}>{reportPayload?.createdAt || "Generated just now"}</Text>
            <Text style={styles.summaryMeta}>
              {reportPayload?.patientName || report.patient_name || "Unnamed patient"}
              {" | "}
              {reportPayload?.patientAge || report.age || "N/A"}
              {" | "}
              {reportPayload?.patientGender || report.gender || "N/A"}
            </Text>
          </View>
          <View style={styles.summaryStatus}>
            <Text style={styles.summaryStatusText}>{editing ? "Editing" : "Ready"}</Text>
          </View>
        </View>
        <View style={styles.summaryActions}>
          <PrimaryButton
            title={editing ? "Save Changes" : "Edit Report"}
            variant="secondary"
            onPress={toggleEditing}
          />
        </View>
      </SectionCard>

      <SectionCard title="Symptoms">
        {editing ? (
          <TextInput
            value={editableReport.symptoms}
            onChangeText={(value) => updateField("symptoms", value)}
            multiline
            textAlignVertical="top"
            placeholder="Enter one symptom per line"
            placeholderTextColor={theme.colors.subtext}
            style={[styles.input, styles.multilineInput]}
          />
        ) : (
          <BulletList items={displayReport.symptoms} />
        )}
      </SectionCard>

      <SectionCard title="Diagnosis">
        {editing ? (
          <TextInput
            value={editableReport.diagnosis}
            onChangeText={(value) => updateField("diagnosis", value)}
            multiline
            textAlignVertical="top"
            placeholder="Enter diagnosis"
            placeholderTextColor={theme.colors.subtext}
            style={[styles.input, styles.multilineInput]}
          />
        ) : (
          <Text style={styles.bodyText}>{displayReport.diagnosis || "No diagnosis available."}</Text>
        )}
      </SectionCard>

      <SectionCard title="Medications">
        {editing ? (
          <TextInput
            value={editableReport.medications}
            onChangeText={(value) => updateField("medications", value)}
            multiline
            textAlignVertical="top"
            placeholder="Enter one medication per line"
            placeholderTextColor={theme.colors.subtext}
            style={[styles.input, styles.multilineInput]}
          />
        ) : (
          <BulletList items={displayReport.medications} />
        )}
      </SectionCard>

      <SectionCard title="Dosage">
        {editing ? (
          <TextInput
            value={editableReport.dosage}
            onChangeText={(value) => updateField("dosage", value)}
            multiline
            textAlignVertical="top"
            placeholder="Enter one dosage instruction per line"
            placeholderTextColor={theme.colors.subtext}
            style={[styles.input, styles.multilineInput]}
          />
        ) : (
          <BulletList items={displayReport.dosage} />
        )}
      </SectionCard>

      <SectionCard title="Precautions">
        {editing ? (
          <TextInput
            value={editableReport.precautions}
            onChangeText={(value) => updateField("precautions", value)}
            multiline
            textAlignVertical="top"
            placeholder="Enter one precaution per line"
            placeholderTextColor={theme.colors.subtext}
            style={[styles.input, styles.multilineInput]}
          />
        ) : (
          <BulletList items={displayReport.precautions} />
        )}
      </SectionCard>

      <SectionCard title="Doctor Notes">
        {editing ? (
          <TextInput
            value={editableReport.doctor_notes}
            onChangeText={(value) => updateField("doctor_notes", value)}
            multiline
            textAlignVertical="top"
            placeholder="Enter doctor notes"
            placeholderTextColor={theme.colors.subtext}
            style={[styles.input, styles.multilineInput]}
          />
        ) : (
          <Text style={styles.bodyText}>{displayReport.doctor_notes || "No doctor notes available."}</Text>
        )}
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
  summaryHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: theme.spacing.md,
  },
  summaryCopy: {
    flex: 1,
    gap: 4,
  },
  summaryTitle: {
    color: theme.colors.text,
    fontSize: 18,
    fontWeight: "800",
  },
  summaryMeta: {
    color: theme.colors.subtext,
    fontSize: 14,
  },
  summaryStatus: {
    backgroundColor: theme.colors.secondary,
    borderRadius: theme.radius.pill,
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: 6,
  },
  summaryStatusText: {
    color: theme.colors.primaryDark,
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  summaryActions: {
    marginTop: theme.spacing.md,
  },
  bodyText: {
    color: theme.colors.text,
    fontSize: 15,
    lineHeight: 23,
  },
  input: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    color: theme.colors.text,
    fontSize: 15,
    lineHeight: 22,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: 12,
  },
  multilineInput: {
    minHeight: 110,
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
