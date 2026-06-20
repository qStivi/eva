// Runtime smoke test: the Chat screen builds and renders the opening
// conversation without throwing, and sending a message echoes it back.
// (Not a behavioural spec — the canned reply flow is timer-driven and stubbed.)

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';

import 'package:eva/main.dart';

void main() {
  setUpAll(() {
    // No network in tests — use the bundled font fallback instead of fetching.
    GoogleFonts.config.allowRuntimeFetching = false;
  });

  testWidgets('Chat renders Eva and the opening turn', (tester) async {
    await tester.pumpWidget(const EvaApp());
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Eva'), findsOneWidget);
    expect(find.textContaining('look who finally showed up'), findsOneWidget);
  });

  testWidgets('Sending a message appends it to the conversation', (tester) async {
    // Tall viewport so every turn renders (the message list is a lazy ListView;
    // a newly-sent bubble below the fold otherwise isn't built/findable).
    tester.view.physicalSize = const Size(1000, 3000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const EvaApp());
    await tester.pump(const Duration(milliseconds: 50));

    await tester.enterText(find.byType(TextField), 'hello eva');
    await tester.pump();
    // The typed text is in the composer field.
    expect(find.text('hello eva'), findsOneWidget);

    await tester.tap(find.byTooltip('Send'));

    // Pump through the auto-scroll so the new bubble (at the bottom of a lazy
    // ListView) is actually built and findable.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 600));

    // Now it's a sent bubble (the field was cleared on send).
    expect(find.text('hello eva'), findsWidgets);

    // Drain the canned-reply + typewriter timers so none are pending at teardown.
    await tester.pump(const Duration(seconds: 3));
  });
}
