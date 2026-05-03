import React, { useEffect, useRef, useState } from "react";
import { Audio } from "expo-av";
import { Alert, StyleSheet, Text, View } from "react-native";

import PrimaryButton from "../components/PrimaryButton";
import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import InputField from "../components/InputField";
import { useAppContext } from "../context/AppContext";
import { theme } from "../theme";

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const secs = (seconds % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
}

export default function RecordScreen({ navigation }) {
  const { logError, logInfo } = useAppContext();
  const [recording, setRecording] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [patientDetails, setPatientDetails] = useState({
    name: "",
    age: "",
    gender: "",
    phone: "",
    notes: "",
  });
  const intervalRef = useRef(null);

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const startTimer = () => {
    intervalRef.current = setInterval(() => {
      setElapsedSeconds((current) => current + 1);
    }, 1000);
  };

  const stopTimer = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const updatePatientField = (field, value) => {
    setPatientDetails((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const handleStartRecording = async () => {
    if (!patientDetails.name.trim()) {
      Alert.alert("Patient name required", "Please add the patient name before recording.");
      return;
    }

    try {
      const permission = await Audio.requestPermissionsAsync();

      if (!permission.granted) {
        logInfo("Microphone permission denied");
        Alert.alert("Microphone access needed", "Please allow microphone access to record audio.");
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );

      setRecording(newRecording);
      setElapsedSeconds(0);
      setIsRecording(true);
      startTimer();
      logInfo("Audio recording started");
    } catch (error) {
      logError("Recording start failed", error);
      Alert.alert("Recording failed", error.message || "Unable to start recording.");
    }
  };

  const handleStopRecording = async () => {
    try {
      stopTimer();
      setIsRecording(false);
      await recording.stopAndUnloadAsync();
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
      });

      const uri = recording.getURI();
      setRecording(null);
      logInfo("Audio recording completed", uri || "no URI returned");

      navigation.replace("Processing", {
        audioAsset: {
          uri,
          name: `consultation-${Date.now()}.m4a`,
          mimeType: "audio/m4a",
        },
        patientDetails,
        sourceLabel: "Recorded audio",
      });
    } catch (error) {
      logError("Recording stop failed", error);
      Alert.alert("Stop failed", error.message || "Unable to finish recording.");
    }
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
          <View style={styles.signalRow}>
            <View style={[styles.signalDot, isRecording && styles.signalDotActive]} />
            <Text style={styles.signalText}>{isRecording ? "Recording in progress" : "Ready to capture audio"}</Text>
          </View>
          <View style={styles.timerBubble}>
            <Text style={styles.timerLabel}>Recording time</Text>
            <Text style={styles.timerValue}>{formatDuration(elapsedSeconds)}</Text>
          </View>
          <View style={styles.buttonStack}>
            {!isRecording ? (
              <PrimaryButton title="Start Recording" onPress={handleStartRecording} />
            ) : (
              <PrimaryButton title="Stop & Generate Report" onPress={handleStopRecording} />
            )}
            <PrimaryButton title="Cancel" variant="secondary" onPress={() => navigation.goBack()} />
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
  buttonStack: {
    marginTop: theme.spacing.md,
    gap: theme.spacing.sm,
  },
});
