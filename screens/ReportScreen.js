import React, { useEffect, useState } from "react";
import { Platform, StyleSheet, Text, TextInput, View } from "react-native";
import * as Linking from "expo-linking";
import * as Sharing from "expo-sharing";

import InputField from "../components/InputField";
import PrimaryButton from "../components/PrimaryButton";
import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import { useAppContext } from "../context/AppContext";
import {
  downloadPdfToCache,
  extractErrorMessage,
  sendReportOnWhatsApp,
  updateReport,
} from "../Services/api";
import { notify } from "../Services/notify";
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
  if (Array.isArray(items)) {
    return items.filter(Boolean).join("\n");
  }
  if (typeof items === "string") {
    return items.trim();
  }
  return "";
}

function toListItems(value) {
  return String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildEditableState(payload) {
  const rep = payload?.report || {};
  return {
    symptoms: toEditableList(rep.symptoms),
    diagnosis: rep.diagnosis || "",
    medications: toEditableList(rep.medications),
    dosage: toEditableList(rep.dosage),
    precautions: toEditableList(rep.precautions),
    follow_up: rep.follow_up || "",
    doctor_notes: rep.doctor_notes || "",
    patient_notes: payload?.patientNotes ?? rep.patient_notes ?? "",
  };
}

export default function ReportScreen({ navigation, route }) {
  const { updateReportEntry } = useAppContext();
  const reportPayload = route.params?.reportPayload;
  const report = reportPayload?.report || {};
  const targetReportId = reportPayload?.reportId || reportPayload?.reportRecordId || reportPayload?.id;

  const [sharing, setSharing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [pdfUrl, setPdfUrl] = useState(reportPayload?.pdfUrl || null);
  const [recipientPhone, setRecipientPhone] = useState(
    reportPayload?.patientPhone || report.patient_phone || report.patient_mobile || ""
  );
  const [editableReport, setEditableReport] = useState(() => buildEditableState(reportPayload));
  const [statusMessage, setStatusMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [needsWhatsAppLink, setNeedsWhatsAppLink] = useState(false);

  useEffect(() => {
    setEditableReport(buildEditableState(reportPayload));
    setPdfUrl(reportPayload?.pdfUrl || null);
    setRecipientPhone(
      reportPayload?.patientPhone ||
        reportPayload?.report?.patient_phone ||
        reportPayload?.report?.patient_mobile ||
        ""
    );
    setEditing(false);
    setStatusMessage("");
    setErrorMessage("");
    setNeedsWhatsAppLink(false);
  }, [reportPayload]);

  const displayReport = {
    symptoms: toListItems(editableReport.symptoms),
    diagnosis: editableReport.diagnosis.trim(),
    medications: toListItems(editableReport.medications),
    dosage: toListItems(editableReport.dosage),
    precautions: toListItems(editableReport.precautions),
    follow_up: editableReport.follow_up.trim(),
    doctor_notes: editableReport.doctor_notes.trim(),
    patient_notes: editableReport.patient_notes.trim(),
  };

  const updateField = (field, value) => {
    setEditableReport((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const handleToggleOrSave = async () => {
    if (!editing) {
      setErrorMessage("");
      setStatusMessage("");
      setEditing(true);
      return;
    }

    const updatedPayload = {
      symptoms: displayReport.symptoms,
      diagnosis: displayReport.diagnosis,
      medications: displayReport.medications,
      dosage: displayReport.dosage,
      precautions: displayReport.precautions,
      follow_up: displayReport.follow_up,
      doctor_notes: displayReport.doctor_notes,
      patient_notes: displayReport.patient_notes,
    };

    if (!targetReportId) {
      setEditing(false);
      setStatusMessage("Changes updated locally.");
      return;
    }

    try {
      setSaving(true);
      setErrorMessage("");
      setStatusMessage("");
      const saved = await updateReport(targetReportId, updatedPayload);
      const refreshedPdf = saved.pdf_url
        ? `${saved.pdf_url}${saved.pdf_url.includes("?") ? "&" : "?"}t=${Date.now()}`
        : pdfUrl;
      if (refreshedPdf) {
        setPdfUrl(refreshedPdf);
      }
      updateReportEntry(targetReportId, {
        report: saved.report || { ...report, ...updatedPayload },
        pdfUrl: refreshedPdf || pdfUrl,
        patientNotes: displayReport.patient_notes,
      });
      setEditing(false);
      setStatusMessage("Changes saved to database and PDF regenerated.");
    } catch (err) {
      const msg = extractErrorMessage(err);
      setErrorMessage(msg);
      notify("Save failed", msg);
    } finally {
      setSaving(false);
    }
  };

  const handleViewPdf = async () => {
    if (!pdfUrl) {
      const msg = "No PDF URL is available for this report.";
      setErrorMessage(msg);
      notify("PDF unavailable", msg);
      return;
    }

    if (Platform.OS === "web") {
      window.open(pdfUrl, "_blank");
      return;
    }

    const canOpen = await Linking.canOpenURL(pdfUrl);
    if (!canOpen) {
      notify("Cannot open PDF", "This device cannot open the PDF URL.");
      return;
    }
    await Linking.openURL(pdfUrl);
  };

  const handleDownloadPdf = async () => {
    if (!pdfUrl) {
      const msg = "No PDF URL is available for this report.";
      setErrorMessage(msg);
      notify("PDF unavailable", msg);
      return;
    }

    const downloadUrl = pdfUrl.includes("?") ? `${pdfUrl}&download=1` : `${pdfUrl}?download=1`;

    if (Platform.OS === "web") {
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `clinical_report_${reportPayload?.patientName || "patient"}.pdf`;
      a.target = "_blank";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      return;
    }

    try {
      const localUri = await downloadPdfToCache(downloadUrl);
      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(localUri);
      } else {
        notify("PDF Downloaded", `Saved to: ${localUri}`);
      }
    } catch (err) {
      const msg = err?.message || "Failed to download PDF.";
      setErrorMessage(msg);
      notify("Download Error", msg);
    }
  };

  const handleSendWhatsApp = async () => {
    if (!targetReportId) {
      setErrorMessage("Report must be saved before sending on WhatsApp.");
      return;
    }

    if (!recipientPhone.trim()) {
      setErrorMessage("Please enter the patient's WhatsApp phone number.");
      return;
    }

    try {
      setSharing(true);
      setErrorMessage("");
      setStatusMessage("");
      setNeedsWhatsAppLink(false);

      const res = await sendReportOnWhatsApp(targetReportId, recipientPhone.trim());
      const msg = `Report PDF sent on WhatsApp to ${res.to || recipientPhone.trim()}.`;
      setStatusMessage(msg);
      notify("Sent on WhatsApp", msg);
    } catch (err) {
      const status = err?.response?.status;
      const msg = extractErrorMessage(err);
      setErrorMessage(msg);
      if (status === 409 || status === 503) {
        setNeedsWhatsAppLink(true);
      }
      notify("WhatsApp Send Failed", msg);
    } finally {
      setSharing(false);
    }
  };

  const ageDisplay = reportPayload?.patientAge ?? report.patient_age ?? report.age;
  const genderDisplay = reportPayload?.patientGender || report.patient_gender || report.gender || "N/A";

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
              {ageDisplay !== null && ageDisplay !== undefined && ageDisplay !== "" ? ageDisplay : "N/A"}
              {" | "}
              {genderDisplay}
            </Text>
          </View>
          <View style={styles.summaryStatus}>
            <Text style={styles.summaryStatusText}>{editing ? "Editing" : "Ready"}</Text>
          </View>
        </View>
        {!!statusMessage && <Text style={styles.successText}>{statusMessage}</Text>}
        {!!errorMessage && <Text style={styles.errorText}>{errorMessage}</Text>}
        {needsWhatsAppLink && (
          <View style={styles.linkAction}>
            <PrimaryButton
              title="Open WhatsApp QR Login"
              onPress={() => navigation.navigate("WhatsAppConnect")}
            />
          </View>
        )}
        <View style={styles.summaryActions}>
          <PrimaryButton
            title={editing ? "Save Changes" : "Edit Report"}
            variant="secondary"
            onPress={handleToggleOrSave}
            loading={saving}
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

      <SectionCard title="Follow-Up">
        {editing ? (
          <TextInput
            value={editableReport.follow_up}
            onChangeText={(value) => updateField("follow_up", value)}
            multiline
            textAlignVertical="top"
            placeholder="Enter follow-up instructions"
            placeholderTextColor={theme.colors.subtext}
            style={[styles.input, styles.multilineInput]}
          />
        ) : (
          <Text style={styles.bodyText}>{displayReport.follow_up || "No follow-up specified."}</Text>
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

      {(editing || !!displayReport.patient_notes) && (
        <SectionCard title="Patient Notes" subtle>
          {editing ? (
            <TextInput
              value={editableReport.patient_notes}
              onChangeText={(value) => updateField("patient_notes", value)}
              multiline
              textAlignVertical="top"
              placeholder="Patient history / notes"
              placeholderTextColor={theme.colors.subtext}
              style={[styles.input, styles.multilineInput]}
            />
          ) : (
            <Text style={styles.bodyText}>{displayReport.patient_notes}</Text>
          )}
        </SectionCard>
      )}

      <SectionCard title="Transcript" subtle>
        <Text style={styles.bodyText}>{reportPayload?.transcript || "Transcript not provided."}</Text>
      </SectionCard>

      <SectionCard title="Share & Export">
        <InputField
          label="Patient WhatsApp Number"
          value={recipientPhone}
          onChangeText={setRecipientPhone}
          placeholder="+91 98xxxxxx12"
          keyboardType="phone-pad"
        />
        <View style={styles.buttonStack}>
          <PrimaryButton
            title="Send PDF on WhatsApp"
            onPress={handleSendWhatsApp}
            loading={sharing}
          />
          <PrimaryButton title="View PDF" variant="secondary" onPress={handleViewPdf} />
          <PrimaryButton
            title="Download PDF"
            variant="secondary"
            onPress={handleDownloadPdf}
          />
        </View>
      </SectionCard>
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
    marginTop: theme.spacing.sm,
  },
  linkAction: {
    marginTop: theme.spacing.xs,
  },
  successText: {
    color: "#166534",
    fontSize: 14,
    fontWeight: "700",
    marginTop: theme.spacing.xs,
  },
  errorText: {
    color: theme.colors.danger,
    fontSize: 14,
    fontWeight: "600",
    marginTop: theme.spacing.xs,
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
    marginTop: theme.spacing.xs,
  },
});
