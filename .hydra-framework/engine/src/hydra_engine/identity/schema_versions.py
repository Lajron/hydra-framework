"""Envelope schema-version constants."""

from __future__ import annotations

from hydra_engine.documents.yaml_documents import yaml_int

# Envelope schema_version, distinct from manifest.yaml's
# seed_version: seed_version tracks the framework release, schema_version
# tracks the shape of the object envelope itself. Objects written before this
# field existed have no schema_version line at all; that is version 0, not an
# error, until `hydra.py schema upgrade` (see objects/schema_upgrades.py) runs.
UNVERSIONED_SCHEMA_VERSION = 0
CURRENT_SCHEMA_VERSION = 3

# uid presence is required from this schema_version onward. Gated on the
# object's own schema_version, not on
# CURRENT_SCHEMA_VERSION, so raising CURRENT_SCHEMA_VERSION for an unrelated
# later migration can never retroactively make an already-compliant object
# fail this check.
UID_REQUIRED_FROM_SCHEMA_VERSION = 2

# The rest of the mandatory envelope is required from this
# schema_version onward, and is gated on the object's own schema_version for
# exactly the reason uid is: a downstream copy that has not run `schema
# upgrade` must never fail for someone else's lag. It is a separate constant
# from UID_REQUIRED_FROM_SCHEMA_VERSION because these fields became mandatory
# in a later migration, and an object still at 2 is compliant with what 2 asked
# of it.
ENVELOPE_REQUIRED_FROM_SCHEMA_VERSION = 3

# Must carry a real value. Absent, these used to be filled in silently with
# plausible stand-ins - "active", "unspecified", a kind read back out of the
# hydra_id - which is the dangerous silence: the envelope read as authored when
# nobody had authored it.
REQUIRED_ENVELOPE_FIELDS = ("kind", "title", "status", "scope", "owners")

# Must be present, and may be empty. This asymmetry is deliberate: an agent
# that cannot name a real relationship or a
# real source must leave the slot empty rather than invent filler. An empty list
# is therefore a real answer here - which is also why these two, alone, are the
# fields an automated migration is allowed to write (see objects/schema_upgrades.py).
EMPTY_ALLOWED_ENVELOPE_FIELDS = ("relations", "provenance.sources")


def envelope_schema_version(data: dict) -> int:
    """The schema_version an already-parsed envelope declares; 0 when absent."""
    return yaml_int(data.get("schema_version"), UNVERSIONED_SCHEMA_VERSION)
