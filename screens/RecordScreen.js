import React, { useEffect, useRef, useState } from "react";
import { Audio } from "expo-av";
import { Platform, StyleSheet, Text, View } from "react-native";

import InputField from "../components/InputField";
import PrimaryButton from "../components/PrimaryButton";
import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import { notify } from "../Services/notify";
import { theme } from "../theme";

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const secs = (seconds % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
}

export default function RecordScreen({ navigation }) {
  const [isRecording, setIsRecording] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState("");
  const [patientDetails, setPatientDetails] = useState({
    name: "",
    age: "",
    gender: "",
    phone: "",
    notes: "",
  });

  const intervalRef = useRef(null);
  const recordingRef = useRef(null);

  const stopTimer = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const cleanupRecording = async () => {
    stopTimer();
    const activeRecording = recordingRef.current;
    recordingRef.current = null;
    if (activeRecording) {
      try {
        await activeRecording.stopAndUnloadAsync();
      } catch {
        // Ignore already-stopped recording cleanup error
      }
      try {
        await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
      } catch {
        // Ignore audio mode reset failure
      }
    }
  };

  useEffect(() => {
    return () => {
      cleanupRecording();
    };
  }, []);

  const startTimer = () => {
    stopTimer();
    intervalRef.current = setInterval(() => {
      setElapsedSeconds((current) => current + 1);
    }, 1000);
  };

  const updatePatientField = (field, value) => {
    setPatientDetails((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const validatePatientDetails = () => {
    if (!patientDetails.name.trim()) {
      return "Please add the patient name before recording.";
    }
    const rawAge = patientDetails.age.trim();
    if (rawAge) {
      const parsedAge = Number(rawAge);
      if (!Number.isInteger(parsedAge) || parsedAge < 0 || parsedAge > 150) {
        return "Patient age must be a whole number between 0 and 150.";
      }
    }
    return "";
  };

  const handleStartRecording = async () => {
    const validationErr = validatePatientDetails();
    if (validationErr) {
      setError(validationErr);
      notify("Patient details", validationErr);
      return;
    }

    try {
      setError("");
      await cleanupRecording();

      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        const msg = "Please allow microphone access to record audio.";
        setError(msg);
        notify("Microphone access needed", msg);
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );

      recordingRef.current = newRecording;
      setElapsedSeconds(0);
      setIsRecording(true);
      startTimer();
    } catch (err) {
      const msg = err?.message || "Unable to start recording.";
      setError(msg);
      notify("Recording failed", msg);
    }
  };

  const handleStopRecording = async () => {
    if (stopping || !recordingRef.current) {
      return;
    }

    try {
      setStopping(true);
      setError("");
      stopTimer();
      setIsRecording(false);

      const activeRecording = recordingRef.current;
      recordingRef.current = null;

      await activeRecording.stopAndUnloadAsync();
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
      });

      const uri = activeRecording.getURI();
      if (!uri) {
        throw new Error("No recorded audio file URI was produced.");
      }

      const defaultExt = Platform.OS === "web" ? "webm" : "m4a";
      const defaultMime = Platform.OS === "web" ? "audio/webm" : "audio/m4a";

      navigation.navigate("Processing", {
        audioAsset: {
          uri,
          name: `consultation-${Date.now()}.${defaultExt}`,
          mimeType: defaultMime,
        },
        patientDetails,
        sourceLabel: "Recorded audio",
      });
    } catch (err) {
      const msg = err?.message || "Unable to finish recording.";
      setError(msg);
      notify("Stop failed", msg);
    } finally {
      setStopping(false);
    }
  };

  const handleCancel = async () => {
    await cleanupRecording();
    setIsRecording(false);
    navigation.goBack();
  };

  return (
    <ScreenContainer>
      <View style={styles.wrapper}>
        <SectionCard title="Live Consultation Capture">
          <Text style={styles.description}>
            Use the built-in recorder to capture a consultation and send it straight to the backend.
          </Text>
          <View style={styles.formStack}>
            <InputField
              label="Patient Name *"
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
              label="Phone (WhatsApp)"
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
          <View style={styles.signalRow}>
            <View style={[styles.signalDot, isRecording && styles.signalDotActive]} />
            <Text style={styles.signalText}>
              {isRecording ? "Recording in progress" : "Ready to capture audio"}
            </Text>
          </View>
          <View style={styles.timerBubble}>
            <Text style={styles.timerLabel}>Recording time</Text>
            <Text style={styles.timerValue}>{formatDuration(elapsedSeconds)}</Text>
          </View>
          {!!error && <Text style={styles.error}>{error}</Text>}
          <View style={styles.buttonStack}>
            {!isRecording ? (
              <PrimaryButton title="Start Recording" onPress={handleStartRecording} disabled={stopping} />
            ) : (
              <PrimaryButton
                title="Stop & Generate Report"
                onPress={handleStopRecording}
                loading={stopping}
              />
            )}
            <PrimaryButton title="Cancel" variant="secondary" onPress={handleCancel} disabled={stopping} />
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
  signalRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: theme.spacing.xs,
    marginTop: theme.spacing.xs,
  },
  formStack: {
    gap: theme.spacing.sm,
    marginTop: theme.spacing.md,
  },
  signalDot: {
    width: 10,
    height: 10,
    borderRadius: theme.radius.pill,
    backgroundColor: theme.colors.borderStrong,
  },
  signalDotActive: {
    backgroundColor: theme.colors.danger,
  },
  signalText: {
    color: theme.colors.subtext,
    fontSize: 13,
    fontWeight: "600",
  },
  timerBubble: {
    marginTop: theme.spacing.md,
    borderRadius: theme.radius.lg,
    paddingVertical: theme.spacing.lg,
    paddingHorizontal: theme.spacing.md,
    alignItems: "center",
    backgroundColor: theme.colors.surfaceMuted,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  timerLabel: {
    color: theme.colors.subtext,
    fontSize: 13,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  timerValue: {
    color: theme.colors.text,
    fontSize: 42,
    fontWeight: "800",
    marginTop: theme.spacing.xs,
  },
  error: {
    color: theme.colors.danger,
    fontSize: 14,
    fontWeight: "600",
    marginTop: theme.spacing.xs,
  },
  buttonStack: {
    marginTop: theme.spacing.md,
    gap: theme.spacing.sm,
  },
});
