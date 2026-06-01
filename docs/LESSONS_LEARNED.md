# Lessons Learned

This public version keeps technical lessons that help future contributors.
Business planning notes were removed before the Day-1 source release.

1. Preserve layer information whenever the user expects to keep editing in
   Illustrator. Use `apply-jsx` or the native-payload path instead of the fast
   PDF-stream rewrite.
2. Treat converted `.ai` files as their own class. They may open in Illustrator
   but still lack `/NumBlock`, so `apply-saas --poche` is not the right path.
3. Poché should fail conservatively. A missing fill is easier to repair than an
   incorrect black mass.
4. Real fixtures matter. Private section dogfood and large-file stress dogfood
   exercise different parts of the system; neither is public proof clearance.
5. Native Illustrator payloads can contain structured, inspectable drawing
   commands. Verify the bytes before assuming an opaque format cannot be
   handled.
6. Long Illustrator bridge runs need heartbeat/progress reporting so users can
   distinguish slow work from a hung process.
7. Keep release docs tied to verified workflows: source/GitHub install,
   Illustrator/Acrobat review, unverified Bluebeam, and local-only webapp
   experiments.
