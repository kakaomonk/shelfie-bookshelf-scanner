import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { confirmBook } from '../api';
import { ScannedBook } from '../types';
import ReviewItem from './ReviewItem';

type Status = 'saving' | 'done' | 'failed';

/** A high-confidence match: "can be added directly" per spec, so it's confirmed automatically
 * with no button to press. If that confirm call itself fails, it falls back to the same manual
 * review card as a low-confidence match -- an auto-add is never silently dropped just because
 * the save request happened to fail. */
export default function AutoAddedItem({ book }: { book: ScannedBook }) {
  const [status, setStatus] = useState<Status>('saving');
  const best = book.match.best_match!;

  useEffect(() => {
    let cancelled = false;
    confirmBook({ title: best.title, author: best.author, catalog_id: best.catalog_id, match_confidence: best.score })
      .then(() => {
        if (!cancelled) setStatus('done');
      })
      .catch(() => {
        if (!cancelled) setStatus('failed');
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [book.index]);

  if (status === 'failed') {
    return <ReviewItem book={book} />;
  }

  return (
    <View style={styles.row}>
      <Text style={styles.text}>{status === 'saving' ? `Adding ${best.title}...` : `Added: ${best.title}`}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { paddingVertical: 8, paddingHorizontal: 4 },
  text: { color: '#2f6690', fontSize: 14 },
});
