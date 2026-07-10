export const generatePassword = (): string => {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';
  const symbols = '!@#$%&*';
  const buf = new Uint32Array(12);
  crypto.getRandomValues(buf);
  let pwd = '';
  for (let i = 0; i < 10; i++) pwd += alphabet[buf[i] % alphabet.length];
  pwd += symbols[buf[10] % symbols.length];
  pwd += buf[11] % 10;
  return pwd;
};
