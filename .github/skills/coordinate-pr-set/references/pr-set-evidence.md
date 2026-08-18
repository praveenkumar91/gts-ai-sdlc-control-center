# PR-set evidence

Each PR record must include:

- repository ID and canonical URL;
- PR number and HTTPS URL;
- base branch and change branch;
- exact tested head SHA;
- required-check conclusion;
- independent approving identities;
- unresolved-conversation count;
- CODEOWNER approval status;
- related change ID and PR-set digest.

Reject approval when:

- any PR is missing;
- a head SHA differs from the tested commit vector;
- a required check is missing, pending, skipped or failed;
- the only reviewer is the requester, author or last-push actor where independent approval is required;
- an approval became stale;
- a required conversation remains unresolved;
- a branch-protection bypass is required.

The orchestrator never calls an approval API. It records external evidence and uses it as a gate.
