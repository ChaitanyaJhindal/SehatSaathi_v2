import React, { useCallback, useEffect, useState } from "react";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";

import InputField from "../components/InputField";
import PrimaryButton from "../components/PrimaryButton";
import ScreenContainer from "../components/ScreenContainer";
import SectionCard from "../components/SectionCard";
import { useAppContext } from "../context/AppContext";
import {
  connectWhatsApp,
  extractErrorMessage,
  getWhatsAppStatus,
  logoutWhatsApp,
  requestWhatsAppPairingCode,
} from "../Services/api";
import { theme } from "../theme";

function getBadgeStyle(statusInfo) {
  if (!statusInfo || statusInfo.status === "service_error" || statusInfo.status === "gateway_offline") {
    return { label: "Unavailable", bg: "#FEE4E2", fg: theme.colors.danger };
  }
  if (statusInfo.connected || statusInfo.status === "ready") {
    return { label: "Connected", bg: "#DCFCE7", fg: "#166534" };
  }
  if (statusInfo.status === "qr_ready") {
    return { label: "Scan QR Code", bg: "#FEF3C7", fg: "#92400E" };
  }
  if (statusInfo.status === "initializing" || statusInfo.status === "authenticating") {
    return { label: "Connecting...", bg: theme.colors.secondary, fg: theme.colors.primaryDark };
  }
  return { label: "Not Linked", bg: theme.colors.surfaceMuted, fg: theme.colors.subtext };
}

export default function WhatsAppConnectScreen() {
  const { whatsappStatus, setWhatsappStatus } = useAppContext();
  const [statusInfo, setStatusInfo] = useState(whatsappStatus);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [infoMsg, setInfoMsg] = useState("");
  const [showPairing, setShowPairing] = useState(false);
  const [pairingPhone, setPairingPhone] = useState("");
  const [pairingCode, setPairingCode] = useState("");

  const syncStatus = useCallback(async () => {
    try {
      const next = await getWhatsAppStatus();
      setStatusInfo(next);
      setWhatsappStatus(next);
      if (next.connected) {
        setPairingCode("");
      }
      return next;
    } catch (err) {
      setError(extractErrorMessage(err));
      return null;
    }
  }, [setWhatsappStatus]);

  useEffect(() => {
    syncStatus();
  }, [syncStatus]);

  useEffect(() => {
    const st = statusInfo?.status;
    if (st !== "initializing" && st !== "qr_ready" && st !== "authenticating" && st !== "created") {
      return undefined;
    }
    const timer = setInterval(() => {
      syncStatus();
    }, 2500);
    return () => clearInterval(timer);
  }, [statusInfo?.status, syncStatus]);

  const handleConnect = async () => {
    try {
      setLoading(true);
      setError("");
      setInfoMsg("");
      const next = await connectWhatsApp();
      setStatusInfo(next);
      setWhatsappStatus(next);
      if (next.connected) {
        setInfoMsg("WhatsApp is connected and ready to send reports.");
      } else if (next.qr_code) {
        setInfoMsg("Scan this QR code in WhatsApp -> Linked Devices.");
      } else {
        setInfoMsg("Connecting to WhatsApp Web... QR code will appear shortly.");
      }
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRequestPairingCode = async () => {
    if (!pairingPhone.trim()) {
      setError("Enter your WhatsApp phone number with country code (e.g. +9198xxxxxxxx).");
      return;
    }
    try {
      setLoading(true);
      setError("");
      setInfoMsg("");
      const res = await requestWhatsAppPairingCode(pairingPhone.trim());
      setStatusInfo(res);
      setWhatsappStatus(res);
      if (res.pairing_code) {
        setPairingCode(res.pairing_code);
        setInfoMsg("Enter this 8-character code in WhatsApp -> Linked Devices -> Link with phone number.");
      } else if (res.connected) {
        setInfoMsg("WhatsApp is already connected.");
      }
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      setLoading(true);
      setError("");
      setInfoMsg("");
      setPairingCode("");
      const next = await logoutWhatsApp();
      setStatusInfo(next);
      setWhatsappStatus(next);
      setInfoMsg("WhatsApp device unlinked.");
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const badge = getBadgeStyle(statusInfo);
  const isConnected = Boolean(statusInfo?.connected);

  return (
    <ScreenContainer>
      <SectionCard title="WhatsApp Web Login">
        <View style={styles.statusRow}>
          <View style={styles.statusCopy}>
            <Text style={styles.statusHeading}>Session Status</Text>
            <Text style={styles.statusMeta}>
              {isConnected
                ? `Linked as ${statusInfo?.push_name || "Doctor"} (${statusInfo?.phone || "Active"})`
                : "Link your WhatsApp once by scanning the QR code to send patient PDF reports directly."}
            </Text>
          </View>
          <View style={[styles.badge, { backgroundColor: badge.bg }]}>
            <Text style={[styles.badgeText, { color: badge.fg }]}>{badge.label}</Text>
          </View>
        </View>

        {!!error && <Text style={styles.error}>{error}</Text>}
        {!!infoMsg && <Text style={styles.info}>{infoMsg}</Text>}
        {!!statusInfo?.last_error && !isConnected && (
          <Text style={styles.error}>{statusInfo.last_error}</Text>
        )}

        {!isConnected && statusInfo?.qr_code && (
          <View style={styles.qrCard}>
            <View style={styles.qrFrame}>
              <Image
                source={{ uri: statusInfo.qr_code }}
                style={styles.qrImage}
                resizeMode="contain"
              />
            </View>
            <Text style={styles.stepsTitle}>How to link:</Text>
            <Text style={styles.stepText}>1. Open WhatsApp on your phone</Text>
            <Text style={styles.stepText}>2. Tap Menu or Settings -&gt; Linked Devices</Text>
            <Text style={styles.stepText}>3. Tap Link a Device and scan this QR code</Text>
          </View>
        )}

        <View style={styles.buttonStack}>
          {!isConnected ? (
            <PrimaryButton
              title={statusInfo?.qr_code ? "Refresh QR Code" : "Connect / Show QR Code"}
              onPress={handleConnect}
              loading={loading}
            />
          ) : (
            <PrimaryButton
              title="Disconnect WhatsApp"
              variant="secondary"
              onPress={handleLogout}
              loading={loading}
            />
          )}
          <PrimaryButton
            title="Check Status"
            variant="secondary"
            onPress={syncStatus}
            disabled={loading}
          />
        </View>
      </SectionCard>

      {!isConnected && (
        <SectionCard title="Alternative Login" subtle>
          <Pressable onPress={() => setShowPairing((prev) => !prev)}>
            <Text style={styles.toggleLink}>
              {showPairing ? "Hide phone-number pairing" : "Or link using phone number (8-char code)"}
            </Text>
          </Pressable>

          {showPairing && (
            <View style={styles.pairingBox}>
              <InputField
                label="Your WhatsApp Number"
                value={pairingPhone}
                onChangeText={setPairingPhone}
                placeholder="+91 98xxxxxxxx"
                keyboardType="phone-pad"
              />
              <PrimaryButton
                title="Get 8-Character Pairing Code"
                variant="secondary"
                onPress={handleRequestPairingCode}
                loading={loading}
              />
              {!!pairingCode && (
                <View style={styles.codeCard}>
                  <Text style={styles.codeLabel}>Pairing Code</Text>
                  <Text style={styles.pairingCode}>{pairingCode}</Text>
                </View>
              )}
            </View>
          )}
        </SectionCard>
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  statusRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: theme.spacing.md,
  },
  statusCopy: {
    flex: 1,
    gap: 4,
  },
  statusHeading: {
    fontSize: 16,
    fontWeight: "800",
    color: theme.colors.text,
  },
  statusMeta: {
    fontSize: 14,
    color: theme.colors.subtext,
    lineHeight: 20,
  },
  badge: {
    borderRadius: theme.radius.pill,
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: 6,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 0.6,
  },
  qrCard: {
    alignItems: "center",
    backgroundColor: theme.colors.surfaceMuted,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing.lg,
    gap: theme.spacing.xs,
  },
  qrFrame: {
    backgroundColor: "#FFFFFF",
    padding: theme.spacing.md,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    marginBottom: theme.spacing.sm,
  },
  qrImage: {
    width: 240,
    height: 240,
  },
  stepsTitle: {
    color: theme.colors.text,
    fontWeight: "800",
    fontSize: 14,
    marginTop: theme.spacing.xs,
  },
  stepText: {
    color: theme.colors.subtext,
    fontSize: 14,
    lineHeight: 20,
    textAlign: "center",
  },
  buttonStack: {
    gap: theme.spacing.sm,
    marginTop: theme.spacing.sm,
  },
  error: {
    color: theme.colors.danger,
    fontSize: 14,
    fontWeight: "600",
  },
  info: {
    color: theme.colors.primaryDark,
    fontSize: 14,
    fontWeight: "600",
  },
  toggleLink: {
    color: theme.colors.primary,
    fontWeight: "700",
    fontSize: 14,
  },
  pairingBox: {
    gap: theme.spacing.sm,
    marginTop: theme.spacing.sm,
  },
  codeCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing.md,
    alignItems: "center",
    gap: 4,
  },
  codeLabel: {
    color: theme.colors.subtext,
    fontSize: 12,
    fontWeight: "700",
    textTransform: "uppercase",
  },
  pairingCode: {
    color: theme.colors.primaryDark,
    fontSize: 28,
    fontWeight: "800",
    letterSpacing: 4,
  },
});
