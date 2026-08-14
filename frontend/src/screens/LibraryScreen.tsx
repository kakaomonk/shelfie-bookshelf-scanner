import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { ApiError, deleteLibraryEntry, fetchLibrary } from '../api';
import { LibraryEntry } from '../types';

type Stage = 'loading' | 'ready' | 'error';

// Remounted each time the user switches to this tab (see App.tsx), which is what triggers the
// refetch below -- no extra "did something change" plumbing needed for a list this small.
export default function LibraryScreen() {
  const [stage, setStage] = useState<Stage>('loading');
  const [entries, setEntries] = useState<LibraryEntry[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await fetchLibrary();
      setEntries(data);
      setStage('ready');
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.message : 'Could not load your library.');
      setStage('error');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onRefresh() {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }

  async function onDelete(id: number) {
    const previous = entries;
    setEntries(entries.filter((e) => e.id !== id));
    try {
      await deleteLibraryEntry(id);
    } catch {
      setEntries(previous); // couldn't delete server-side -- don't leave the UI out of sync
    }
  }

  if (stage === 'loading') {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (stage === 'error') {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>{errorMessage}</Text>
        <TouchableOpacity style={styles.button} onPress={load}>
          <Text style={styles.buttonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <FlatList
      contentContainerStyle={styles.container}
      data={entries}
      keyExtractor={(item) => String(item.id)}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      ListHeaderComponent={<Text style={styles.heading}>My Library ({entries.length})</Text>}
      ListEmptyComponent={<Text style={styles.statusText}>No books yet -- scan a shelf to get started.</Text>}
      renderItem={({ item }) => (
        <View style={styles.row}>
          <View style={styles.info}>
            <Text style={styles.title}>{item.title}</Text>
            {!!item.author && <Text style={styles.author}>{item.author}</Text>}
          </View>
          <TouchableOpacity onPress={() => onDelete(item.id)}>
            <Text style={styles.remove}>Remove</Text>
          </TouchableOpacity>
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, paddingTop: 60, gap: 4 },
  heading: { fontSize: 24, fontWeight: '700', marginBottom: 12 },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12, paddingTop: 100 },
  statusText: { fontSize: 16, color: '#444' },
  errorText: { fontSize: 15, color: '#b00020', textAlign: 'center', paddingHorizontal: 20 },
  button: { backgroundColor: '#2f6690', paddingVertical: 12, paddingHorizontal: 20, borderRadius: 10 },
  buttonText: { color: 'white', fontWeight: '600' },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  info: { flex: 1 },
  title: { fontSize: 16, fontWeight: '600' },
  author: { fontSize: 14, color: '#555', marginTop: 2 },
  remove: { color: '#b00020', fontSize: 13 },
});
