export const CREDENTIAL_FILE_MAX_BYTES = 1024 * 1024;

/** Rejected credential file; the message is the i18n key of the explanation. */
export class CredentialFileError extends Error {}

/** Parse a provider credential file. */
export async function readCredentialFile(file: File): Promise<unknown> {
  if (file.size > CREDENTIAL_FILE_MAX_BYTES) throw new CredentialFileError("accounts.credentialImport.tooLarge");
  try {
    return JSON.parse(await file.text());
  } catch {
    throw new CredentialFileError("accounts.credentialImport.invalidJson");
  }
}
