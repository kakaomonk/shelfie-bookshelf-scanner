import { useState } from 'react';
import { Image, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';

import { ApiError, confirmBook, resolveMediaUrl } from '../api';
import { ScannedBook } from '../types';

type LocalStatus = 'pending' | 'saving' | 'confirmed' | 'discarded' | 'error';

export default function ReviewItem({ book }: { book: ScannedBook }) {
  const suggestion = book.match.best_match;
  const [title, setTitle] = useState(suggestion?.title ?? book.read.title);
  const [author, setAuthor] = useState(suggestion?.author ?? book.read.author);
  const [catalogId, setCatalogId] = useState<number | null>(suggestion?.catalog_id ?? null);
  const [matchScore, setMatchScore] = useState<number | null>(suggestion?.score ?? null);
  const [status, setStatus] = useState<LocalStatus>('pending');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const alternatives = book.match.candidates.filter((c) => c.catalog_id !== suggestion?.catalog_id);

  function applyEdit(field: 'title' | 'author', value: string) {
    // Once the user edits away from the suggested match, it's no longer that catalog entry --
    // this is stored as a free-text correction rather than re-matched against the catalog.
    setCatalogId(null);
    setMatchScore(null);
    if (field === 'title') setTitle(value);
    else setAuthor(value);
  }

  function applySuggestion(candidateTitle: string, candidateAuthor: string, id: number, score: number) {
    setTitle(candidateTitle);
    setAuthor(candidateAuthor);
    setCatalogId(id);
    setMatchScore(score);
  }

  async function handleConfirm() {
    if (!title.trim()) return;
    setStatus('saving');
    setErrorMessage(null);
    try {
      await confirmBook({ title: title.trim(), author: author.trim(), catalog_id: catalogId, match_confidence: matchScore });
      setStatus('confirmed');
    } catch (err) {
      setStatus('error');
      setErrorMessage(err instanceof ApiError ? err.message : 'Could not save this book.');
    }
  }

  function handleDiscard() {
    setStatus('discarded');
  }

  const cropUrl = resolveMediaUrl(book.crop_url);

  if (status === 'confirmed') {
    return (
      <View style={styles.resolvedRow}>
        <Text style={styles.resolvedText}>Added: {title}</Text>
      </View>
    );
  }
  if (status === 'discarded') {
    return (
      <View style={styles.resolvedRow}>
        <Text style={styles.resolvedTextMuted}>Discarded ({book.read.title || 'unreadable spine'})</Text>
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <View style={styles.row}>
        {cropUrl && <Image source={{ uri: cropUrl }} style={styles.thumbnail} />}
        <View style={styles.fields}>
          <Text style={styles.label}>Title</Text>
          <TextInput style={styles.input} value={title} onChangeText={(v) => applyEdit('title', v)} placeholder="Title" />
          <Text style={styles.label}>Author</Text>
          <TextInput style={styles.input} value={author} onChangeText={(v) => applyEdit('author', v)} placeholder="Author" />
        </View>
      </View>

      {!book.read.legible && <Text style={styles.hint}>Couldn't read this spine -- enter the book manually or discard it.</Text>}
      {matchScore !== null && <Text style={styles.hint}>Suggested match confidence: {Math.round(matchScore * 100)}%</Text>}

      {alternatives.length > 0 && (
        <View style={styles.altRow}>
          <Text style={styles.hint}>Did you mean:</Text>
          {alternatives.map((c) => (
            <TouchableOpacity
              key={c.catalog_id}
              style={styles.chip}
              onPress={() => applySuggestion(c.title, c.author, c.catalog_id, c.score)}
            >
              <Text style={styles.chipText}>{c.title}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {errorMessage && <Text style={styles.errorText}>{errorMessage}</Text>}

      <View style={styles.actionsRow}>
        <TouchableOpacity style={[styles.actionButton, styles.confirmButton]} onPress={handleConfirm} disabled={status === 'saving'}>
          <Text style={styles.actionButtonText}>{status === 'saving' ? 'Saving...' : 'Confirm'}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.actionButton, styles.discardButton]} onPress={handleDiscard} disabled={status === 'saving'}>
          <Text style={styles.actionButtonText}>Discard</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderColor: '#e2e2e2', borderRadius: 10, padding: 12, gap: 8 },
  row: { flexDirection: 'row', gap: 12 },
  thumbnail: { width: 56, height: 84, borderRadius: 4, backgroundColor: '#eee' },
  fields: { flex: 1, gap: 4 },
  label: { fontSize: 11, color: '#777', textTransform: 'uppercase' },
  input: { borderBottomWidth: 1, borderBottomColor: '#ccc', paddingVertical: 4, fontSize: 15 },
  hint: { fontSize: 12, color: '#777' },
  altRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, alignItems: 'center' },
  chip: { backgroundColor: '#eef4fa', borderRadius: 14, paddingHorizontal: 10, paddingVertical: 4 },
  chipText: { fontSize: 12, color: '#2f6690' },
  errorText: { fontSize: 12, color: '#b00020' },
  actionsRow: { flexDirection: 'row', gap: 10, marginTop: 4 },
  actionButton: { flex: 1, paddingVertical: 10, borderRadius: 8, alignItems: 'center' },
  confirmButton: { backgroundColor: '#2f6690' },
  discardButton: { backgroundColor: '#8a8a8a' },
  actionButtonText: { color: 'white', fontWeight: '600' },
  resolvedRow: { paddingVertical: 8, paddingHorizontal: 4 },
  resolvedText: { color: '#2f6690', fontSize: 14 },
  resolvedTextMuted: { color: '#999', fontSize: 14 },
});
