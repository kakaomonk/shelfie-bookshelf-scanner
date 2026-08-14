import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { SafeAreaView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import LibraryScreen from './src/screens/LibraryScreen';
import ScanScreen from './src/screens/ScanScreen';

type Tab = 'scan' | 'library';

export default function App() {
  const [tab, setTab] = useState<Tab>('scan');

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.screen}>{tab === 'scan' ? <ScanScreen /> : <LibraryScreen />}</View>
      <View style={styles.tabBar}>
        <TouchableOpacity style={styles.tabButton} onPress={() => setTab('scan')}>
          <Text style={[styles.tabLabel, tab === 'scan' && styles.tabLabelActive]}>Scan</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.tabButton} onPress={() => setTab('library')}>
          <Text style={[styles.tabLabel, tab === 'library' && styles.tabLabelActive]}>Library</Text>
        </TouchableOpacity>
      </View>
      <StatusBar style="auto" />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  screen: { flex: 1 },
  tabBar: { flexDirection: 'row', borderTopWidth: 1, borderTopColor: '#eee' },
  tabButton: { flex: 1, paddingVertical: 14, alignItems: 'center' },
  tabLabel: { fontSize: 15, color: '#999', fontWeight: '600' },
  tabLabelActive: { color: '#2f6690' },
});
