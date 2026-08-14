import { StatusBar } from 'expo-status-bar';
import { SafeAreaView, StyleSheet } from 'react-native';

import ScanScreen from './src/screens/ScanScreen';

export default function App() {
  return (
    <SafeAreaView style={styles.container}>
      <ScanScreen />
      <StatusBar style="auto" />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
});
