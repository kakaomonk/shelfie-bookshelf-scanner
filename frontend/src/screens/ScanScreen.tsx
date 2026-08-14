import * as ImagePicker from 'expo-image-picker';
import { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import { ApiError, resolveMediaUrl, scanPhoto } from '../api';
import { ScanResponse } from '../types';

type Stage = 'idle' | 'uploading' | 'done' | 'error';

const MATCH_LABEL: Record<string, string> = {
  matched: 'Added to library',
  review: 'Needs review',
  unmatched: 'Not in catalog',
};

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

          {result.books.map((book) => {
            const cropUrl = resolveMediaUrl(book.crop_url);
            return (
              <View key={book.index} style={styles.bookRow}>
                {cropUrl && <Image source={{ uri: cropUrl }} style={styles.thumbnail} />}
                <View style={styles.bookInfo}>
                  <Text style={styles.bookTitle}>
                    {book.match.best_match?.title || book.read.title || '(unreadable spine)'}
                  </Text>
                  <Text style={styles.bookAuthor}>{book.match.best_match?.author || book.read.author}</Text>
                  <Text style={styles.bookStatus}>{MATCH_LABEL[book.match.status]}</Text>
                </View>
              </View>
            );
          })}

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
  bookRow: { flexDirection: 'row', gap: 12, alignItems: 'center', paddingVertical: 6 },
  thumbnail: { width: 48, height: 72, borderRadius: 4, backgroundColor: '#eee' },
  bookInfo: { flex: 1 },
  bookTitle: { fontSize: 16, fontWeight: '600' },
  bookAuthor: { fontSize: 14, color: '#555' },
  bookStatus: { fontSize: 12, color: '#2f6690', marginTop: 2 },
});
