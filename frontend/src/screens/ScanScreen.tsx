import * as ImagePicker from 'expo-image-picker';
import { useState } from 'react';
import { ActivityIndicator, Alert, Image, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { ApiError, scanPhoto } from '../api';
import AutoAddedItem from '../components/AutoAddedItem';
import ReviewItem from '../components/ReviewItem';
import { ScanResponse } from '../types';

type Stage = 'idle' | 'uploading' | 'done' | 'error';

export default function ScanScreen() {
  const [stage, setStage] = useState<Stage>('idle');
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function runScan(uri: string) {
    setPhotoUri(uri);
    setStage('uploading');
    setErrorMessage(null);
    try {
      const response = await scanPhoto(uri);
      setResult(response);
      setStage('done');
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.message : 'Something went wrong scanning that photo.');
      setStage('error');
    }
  }

  async function takePhoto() {
    const { granted } = await ImagePicker.requestCameraPermissionsAsync();
    if (!granted) {
      Alert.alert('Camera permission needed', 'Allow camera access to photograph a bookshelf.');
      return;
    }
    const picked = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.8 });
    if (!picked.canceled && picked.assets[0]) {
      runScan(picked.assets[0].uri);
    }
  }

  async function pickPhoto() {
    const { granted } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!granted) {
      Alert.alert('Photo library permission needed', 'Allow photo access to pick a bookshelf picture.');
      return;
    }
    const picked = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.8 });
    if (!picked.canceled && picked.assets[0]) {
      runScan(picked.assets[0].uri);
    }
  }

  function reset() {
    setStage('idle');
    setPhotoUri(null);
    setResult(null);
    setErrorMessage(null);
  }

  const autoAdded = result?.books.filter((b) => b.match.status === 'matched') ?? [];
  const needsReview = result?.books.filter((b) => b.match.status !== 'matched') ?? [];

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.heading}>Scan a bookshelf</Text>

      {stage === 'idle' && (
        <View style={styles.actions}>
          <TouchableOpacity style={styles.button} onPress={takePhoto}>
            <Text style={styles.buttonText}>Take Photo</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.button, styles.secondaryButton]} onPress={pickPhoto}>
            <Text style={styles.buttonText}>Choose from Library</Text>
          </TouchableOpacity>
        </View>
      )}

      {photoUri && (stage === 'uploading' || stage === 'done' || stage === 'error') && (
        <Image source={{ uri: photoUri }} style={styles.preview} resizeMode="cover" />
      )}

      {stage === 'uploading' && (
        <View style={styles.centered}>
          <ActivityIndicator size="large" />
          <Text style={styles.statusText}>Scanning your shelf...</Text>
        </View>
      )}

      {stage === 'error' && (
        <View style={styles.centered}>
          <Text style={styles.errorText}>{errorMessage}</Text>
          <TouchableOpacity style={styles.button} onPress={reset}>
            <Text style={styles.buttonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      )}

      {stage === 'done' && result && (
        <View style={styles.results}>
          {result.warnings.map((warning, i) => (
            <Text key={i} style={styles.warning}>
              {warning}
            </Text>
          ))}

          {result.books.length === 0 && <Text style={styles.statusText}>No books found in this photo.</Text>}

          {autoAdded.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Added automatically ({autoAdded.length})</Text>
              {autoAdded.map((book) => (
                <AutoAddedItem key={book.index} book={book} />
              ))}
            </View>
          )}

          {needsReview.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Needs your review ({needsReview.length})</Text>
              {needsReview.map((book) => (
                <ReviewItem key={book.index} book={book} />
              ))}
            </View>
          )}

          <TouchableOpacity style={styles.button} onPress={reset}>
            <Text style={styles.buttonText}>Scan Another</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, paddingTop: 60, gap: 16 },
  heading: { fontSize: 24, fontWeight: '700' },
  actions: { gap: 12, marginTop: 12 },
  button: { backgroundColor: '#2f6690', padding: 14, borderRadius: 10, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#5a5a5a' },
  buttonText: { color: 'white', fontWeight: '600', fontSize: 16 },
  preview: { width: '100%', height: 220, borderRadius: 10, marginTop: 8 },
  centered: { alignItems: 'center', gap: 12, marginTop: 20 },
  statusText: { fontSize: 16, color: '#444' },
  errorText: { fontSize: 15, color: '#b00020', textAlign: 'center' },
  results: { gap: 10, marginTop: 8 },
  warning: { color: '#8a6d00', backgroundColor: '#fff4d6', padding: 10, borderRadius: 8 },
  section: { gap: 10, marginTop: 8 },
  sectionTitle: { fontSize: 15, fontWeight: '700', color: '#333' },
});
