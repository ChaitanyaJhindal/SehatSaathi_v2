import React, { useState } from "react";
import { Alert, StyleSheet, Text, View } from "react-native";
import * as DocumentPicker from "expo-document-picker";

import PrimaryButton from "../components/PrimaryButton";
import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import InputField from "../components/InputField";
import { useAppContext } from "../context/AppContext";
import { theme } from "../theme";

export default function UploadScreen({ navigation }) {
  const { logError, logInfo } = useAppContext();
  const [selectedFile, setSelectedFile] = useState(null);
  const [patientDetails, setPatientDetails] = useState({
    name: "",
    age: "",
    gender: "",
    phone: "",
    notes: "",
  });

  const updatePatientField = (field, value) => {
    setPatientDetails((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const handlePickFile = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ["audio/*"],
        copyToCacheDirectory: true,
      });

      if (result.canceled) {
        logInfo("Document picker cancelled");
        return;
      }

      setSelectedFile(result.assets[0]);
      logInfo("Audio file selected", result.assets[0]?.name || result.assets[0]?.uri || "unknown file");
    } catch (error) {
      logError("Document picker failed", error);
      Alert.alert("Upload failed", error.message || "Unable to open the document picker.");
    }
  };

  const handleGenerate = () => {
    if (!selectedFile) {
      Alert.alert("No file selected", "Please choose an audio file first.");
      return;
    }

    if (!patientDetails.name.trim()) {
      Alert.alert("Patient name required", "Please add the patient name before generating the report.");
      return;
    }

    logInfo("Navigating to processing screen", selectedFile.name || "uploaded audio");
    navigation.replace("Processing", {
      audioAsset: selectedFile,
      patientDetails,
      sourceLabel: selectedFile.name || "Uploaded audio",
    });
  };

  return (
    <ScreenContainer>
      <View style={styles.wrapper}>
        <SectionCard title="Upload Existing Audio">
          <Text style={styles.description}>
            Pick a consultation file from your device. SehatSaathi will transcribe it and generate a report.
          </Text>

          <View style={styles.formStack}>
            <InputField
              label="Patient Name"
              value={patientDetails.name}
              onChangeText={(value) => updatePatientField("name", value)}
              placeholder="Rohan Verma"
              autoCapitalize="words"
            />
            <InputField
              label="Age"
              value={patientDetails.age}
              onChangeText={(value) => updatePatientField("age", value)}
              placeholder="42"
              keyboardType="number-pad"
            />
            <InputField
              label="Gender"
              value={patientDetails.gender}
              onChangeText={(value) => updatePatientField("gender", value)}
              placeholder="Male / Female / Other"
              autoCapitalize="words"
            />
            <InputField
              label="Phone"
              value={patientDetails.phone}
              onChangeText={(value) => updatePatientField("phone", value)}
              placeholder="+91 98xxxxxx12"
              keyboardType="phone-pad"
            />
            <InputField
              label="Notes"
              value={patientDetails.notes}
              onChangeText={(value) => updatePatientField("notes", value)}
              placeholder="Known diabetes, follow-up visit"
              autoCapitalize="sentences"
            />
          </View>

          <View style={styles.fileCard}>
            <Text style={styles.fileLabel}>Selected File</Text>
            <Text style={styles.fileName}>{selectedFile?.name || "No file selected yet"}</Text>
            <Text style={styles.fileSubtext}>
              {selectedFile?.mimeType || "Supported formats: m4a, mp3, wav"}
            </Text>
          </View>

          <View style={styles.buttonStack}>
            <PrimaryButton title="Choose Audio File" onPress={handlePickFile} />
            <PrimaryButton title="Generate Report" variant="secondary" onPress={handleGenerate} />
          </View>
        </SectionCard>
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    gap: theme.spacing.md,
  },
  description: {
    color: theme.colors.subtext,
    fontSize: 15,
    lineHeight: 22,
  },
  formStack: {
    gap: theme.spacing.sm,
    marginTop: theme.spacing.md,
  },
  fileCard: {
    backgroundColor: theme.colors.surfaceMuted,
    borderColor: theme.colors.border,
    borderWidth: 1,
    borderRadius: theme.radius.md,
    padding: theme.spacing.md,
    marginTop: theme.spacing.md,
    gap: 6,
  },
  fileLabel: {
    color: theme.colors.primary,
    fontWeight: "800",
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  fileName: {
    color: theme.colors.text,
    fontWeight: "700",
    fontSize: 16,
  },
  fileSubtext: {
    color: theme.colors.subtext,
    fontSize: 13,
  },
  buttonStack: {
    marginTop: theme.spacing.md,
    gap: theme.spacing.sm,
  },
});
