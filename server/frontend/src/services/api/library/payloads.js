export function pickPayloadFields(data, fields) {
  const source = data && typeof data === 'object' ? data : {}
  return Object.fromEntries(
    fields
      .filter((field) => Object.prototype.hasOwnProperty.call(source, field))
      .map((field) => [field, source[field]])
      .filter(([, value]) => value !== undefined)
  )
}
