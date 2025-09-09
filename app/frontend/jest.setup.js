import "@testing-library/jest-dom";
// Learn more: https://github.com/testing-library/jest-dom
import { TextEncoder, TextDecoder } from "util";

// Polyfill for `TextEncoder` and `TextDecoder`
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
