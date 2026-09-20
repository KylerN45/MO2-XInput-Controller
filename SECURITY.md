# Security policy

Please report security-sensitive issues privately through GitHub's security
advisory feature rather than a public issue.

The plugin intentionally loads XInput only by absolute path from Windows'
System32 directory. It does not download code, inject input, or launch
executables directly; Run actions go through MO2's existing button and launch
path.
