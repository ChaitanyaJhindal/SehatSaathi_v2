import React, { useState } from "react";
import { Alert, StyleSheet, Text, View } from "react-native";
import * as DocumentPicker from "expo-document-picker";

import PrimaryButton from "../components/PrimaryButton";
import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import { theme } from "../theme";

export default function UploadScreen({ navigation }) {
  const [selectedFile, setSelectedFile] = useState(null);

  const handlePickFile = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ["audio/*"],
        copyToCacheDirectory: true,
      });

      if (result.canceled) {
        return;
      }

      setSelectedFile(result.assets[0]);
    } catch (error) {
      Alert.alert("Upload failed", error.message || "Unable to open the document picker.");
    }
  };

  const handleGenerate = () => {
    if (!selectedFile) {
      Alert.alert("No file selected", "Please choose an audio file first.");
      return;
    }

    navigation.replace("Processing", {
      audioAsset: selectedFile,
      sourceLabel: selectedFile.name || "Uploaded audio",
    });
  };

  return (
    <ScreenContainer scroll={false}>
      <View style={styles.wrapper}>
        <SectionCard title="Upload Existing Audio">
          <Text style={styles.description}>
            Pick a consultation file from your device. SehatSaathi will transcribe it and generate a report.
          </Text>

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
    flex: 1,
    justifyContent: "center",
  },
  description: {
    color: theme.colors.subtext,
    fontSize: 15,
    lineHeight: 22,
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
    fontSize: 13,
    textTransform: "uppercase",
    letterSpacing: 0.8,
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
