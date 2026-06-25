DeepSeek 专家模式-------------------------------------------------------try1
我（github.com/Emaginations）将要开发一个maibot插件，名字叫做麦麦解析（NCMai），用来解码用户从QQ发送给Maibot的ncm文件。需要提前声明的是：1.本插件、插件产生的文件仅用于技术学习交流，产生的文件请于24h之内删除，不得用于任何商业用途。2.感谢群友termux提供的源代码。

工作流：接收到.ncm格式文件-》建立缓存-》在async函数内解码并发送一句随机表内（含21句正在解码相关的10字内语句含emoji）的消息到对应聊天流-》将解码后的文件缓存-》跟据onebot协议用send_private_msg 发送私聊消息
send_group_msg 发送群消息（或者等我看一下snowluma插件）发回文件-》清理缓存。

现在，请向我普及一下相关的法律知识以及我应该如何改进、选用哪个协议，我将于稍后向你提供所有的插件开发参考文档、解码核心c代码、windows版本的编译器代码、以及我自己的插件示例。

*插件开发参考文档


*解码核心c代码
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#ifdef NCMGUI
#include <commdlg.h>
#endif

typedef unsigned char u8;
typedef unsigned int u32;
typedef unsigned long long u64;

#define STATUS_OK(x) ((NTSTATUS)(x) >= 0)

void *memcpy(void *dst, const void *src, size_t n) {
    u8 *d = (u8 *)dst;
    const u8 *s = (const u8 *)src;
    while (n--) *d++ = *s++;
    return dst;
}

static const u8 NCM_MAGIC[8] = { 'C','T','E','N','F','D','A','M' };
static const u8 CORE_KEY[16] = { 'h','z','H','R','A','m','s','o','5','k','I','n','b','a','x','W' };
static const u8 META_KEY[16] = { '#','1','4','l','j','k','_','!','\\',']','&','0','U','<','\'','(' };

static void outa(const char *s) {
    DWORD n = 0, len = 0;
    while (s[len]) len++;
    WriteFile(GetStdHandle(STD_ERROR_HANDLE), s, len, &n, 0);
}

#ifdef NCMGUI
#define LOGA(x) ((void)0)
#else
#define LOGA(x) outa(x)
#endif

static int eq8(const u8 *a, const u8 *b) {
    u32 i;
    for (i = 0; i < 8; i++) if (a[i] != b[i]) return 0;
    return 1;
}

static u32 rd32(const u8 *p) {
    return (u32)p[0] | ((u32)p[1] << 8) | ((u32)p[2] << 16) | ((u32)p[3] << 24);
}

static void xorb(u8 *p, u32 n, u8 v) {
    u32 i;
    for (i = 0; i < n; i++) p[i] ^= v;
}

static void copyb(u8 *d, const u8 *s, u32 n) {
    u32 i;
    for (i = 0; i < n; i++) d[i] = s[i];
}

static u8 *alloc(u32 n) {
    return (u8 *)HeapAlloc(GetProcessHeap(), 0, n ? n : 1);
}

static void freep(void *p) {
    if (p) HeapFree(GetProcessHeap(), 0, p);
}

static int read_all(const WCHAR *path, u8 **data, u32 *size) {
    HANDLE h = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, 0, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, 0);
    LARGE_INTEGER li;
    DWORD got = 0;
    if (h == INVALID_HANDLE_VALUE) return 0;
    if (!GetFileSizeEx(h, &li) || li.QuadPart <= 0 || li.QuadPart > 0x7fffffff) {
        CloseHandle(h);
        return 0;
    }
    *size = (u32)li.QuadPart;
    *data = alloc(*size);
    if (!*data) {
        CloseHandle(h);
        return 0;
    }
    if (!ReadFile(h, *data, *size, &got, 0) || got != *size) {
        CloseHandle(h);
        freep(*data);
        *data = 0;
        return 0;
    }
    CloseHandle(h);
    return 1;
}

static int write_all(const WCHAR *path, const u8 *data, u32 size) {
    HANDLE h = CreateFileW(path, GENERIC_WRITE, 0, 0, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, 0);
    DWORD done = 0;
    if (h == INVALID_HANDLE_VALUE) return 0;
    while (done < size) {
        DWORD chunk = size - done;
        DWORD wrote = 0;
        if (chunk > 0x100000) chunk = 0x100000;
        if (!WriteFile(h, data + done, chunk, &wrote, 0) || wrote == 0) {
            CloseHandle(h);
            return 0;
        }
        done += wrote;
    }
    CloseHandle(h);
    return 1;
}

static int write_two(const WCHAR *path, const u8 *a, u32 an, const u8 *b, u32 bn) {
    HANDLE h = CreateFileW(path, GENERIC_WRITE, 0, 0, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, 0);
    DWORD w = 0;
    if (h == INVALID_HANDLE_VALUE) return 0;
    if (an && (!WriteFile(h, a, an, &w, 0) || w != an)) { CloseHandle(h); return 0; }
    if (bn && (!WriteFile(h, b, bn, &w, 0) || w != bn)) { CloseHandle(h); return 0; }
    CloseHandle(h);
    return 1;
}

static int aes_ecb_dec(const u8 *in, u32 in_len, const u8 key[16], u8 **out, u32 *out_len) {
    BCRYPT_ALG_HANDLE alg = 0;
    BCRYPT_KEY_HANDLE kh = 0;
    DWORD obj_len = 0, cb = 0, plain_len = 0;
    u8 *obj = 0, *plain = 0;
    int ok = 0;

    if ((in_len & 15) != 0) return 0;
    if (!STATUS_OK(BCryptOpenAlgorithmProvider(&alg, BCRYPT_AES_ALGORITHM, 0, 0))) goto done;
    if (!STATUS_OK(BCryptSetProperty(alg, BCRYPT_CHAINING_MODE, (PUCHAR)BCRYPT_CHAIN_MODE_ECB, sizeof(BCRYPT_CHAIN_MODE_ECB), 0))) goto done;
    if (!STATUS_OK(BCryptGetProperty(alg, BCRYPT_OBJECT_LENGTH, (PUCHAR)&obj_len, sizeof(obj_len), &cb, 0))) goto done;
    obj = alloc(obj_len);
    plain = alloc(in_len);
    if (!obj || !plain) goto done;
    if (!STATUS_OK(BCryptGenerateSymmetricKey(alg, &kh, obj, obj_len, (PUCHAR)key, 16, 0))) goto done;
    if (!STATUS_OK(BCryptDecrypt(kh, (PUCHAR)in, in_len, 0, 0, 0, plain, in_len, &plain_len, 0))) goto done;
    if (plain_len > 0) {
        u8 pad = plain[plain_len - 1];
        if (pad > 0 && pad <= 16 && pad <= plain_len) {
            u32 i, good = 1;
            for (i = plain_len - pad; i < plain_len; i++) {
                if (plain[i] != pad) good = 0;
            }
            if (good) plain_len -= pad;
        }
    }
    *out = plain;
    *out_len = plain_len;
    plain = 0;
    ok = 1;

done:
    if (kh) BCryptDestroyKey(kh);
    if (alg) BCryptCloseAlgorithmProvider(alg, 0);
    freep(obj);
    freep(plain);
    return ok;
}

static void build_keybox(const u8 *key, u32 key_len, u8 box[256]) {
    u32 i, key_offset = 0, last = 0;
    for (i = 0; i < 256; i++) box[i] = (u8)i;
    for (i = 0; i < 256; i++) {
        u8 swap = box[i];
        u32 c = (swap + last + key[key_offset]) & 0xff;
        key_offset++;
        if (key_offset >= key_len) key_offset = 0;
        box[i] = box[c];
        box[c] = swap;
        last = c;
    }
}

static void decrypt_audio(u8 *p, u32 n, const u8 box[256]) {
    u32 i;
    for (i = 0; i < n; i++) {
        u32 j = (i + 1) & 0xff;
        u8 k = box[(box[j] + box[(box[j] + j) & 0xff]) & 0xff];
        p[i] ^= k;
    }
}

static int starts(const u8 *p, u32 n, const char *s) {
    u32 i = 0;
    while (s[i]) {
        if (i >= n || p[i] != (u8)s[i]) return 0;
        i++;
    }
    return 1;
}

#ifdef NCMTAGS
typedef struct TagInfo {
    u8 *title; u32 title_n;
    u8 *artist; u32 artist_n;
    u8 *album; u32 album_n;
    const u8 *cover; u32 cover_n;
} TagInfo;

static int hval(u8 c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static void put_utf8(u8 *o, u32 *n, u32 cp) {
    if (cp < 0x80) o[(*n)++] = (u8)cp;
    else if (cp < 0x800) {
        o[(*n)++] = (u8)(0xc0 | (cp >> 6));
        o[(*n)++] = (u8)(0x80 | (cp & 0x3f));
    } else {
        o[(*n)++] = (u8)(0xe0 | (cp >> 12));
        o[(*n)++] = (u8)(0x80 | ((cp >> 6) & 0x3f));
        o[(*n)++] = (u8)(0x80 | (cp & 0x3f));
    }
}

static u8 *json_str(const u8 *p, const u8 *end, u32 *out_n) {
    u8 *o;
    u32 n = 0;
    if (p >= end || *p != '"') return 0;
    p++;
    o = alloc((u32)(end - p) + 1);
    if (!o) return 0;
    while (p < end && *p != '"') {
        if (*p == '\\' && p + 1 < end) {
            p++;
            if (*p == 'u' && p + 4 < end) {
                int a = hval(p[1]), b = hval(p[2]), c = hval(p[3]), d = hval(p[4]);
                if (a >= 0 && b >= 0 && c >= 0 && d >= 0) {
                    put_utf8(o, &n, (u32)((a << 12) | (b << 8) | (c << 4) | d));
                    p += 5;
                    continue;
                }
            }
            if (*p == 'n') o[n++] = '\n';
            else if (*p == 't') o[n++] = '\t';
            else o[n++] = *p;
            p++;
        } else {
            o[n++] = *p++;
        }
    }
    o[n] = 0;
    *out_n = n;
    return o;
}

static const u8 *find_key(const u8 *p, const u8 *end, const char *key) {
    u32 k = 0, i;
    while (key[k]) k++;
    for (; p + k + 2 < end; p++) {
        if (*p != '"') continue;
        for (i = 0; i < k && p[1 + i] == (u8)key[i]; i++);
        if (i == k && p[1 + k] == '"') {
            p += k + 2;
            while (p < end && (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')) p++;
            if (p < end && *p == ':') return p + 1;
        }
    }
    return 0;
}

static u8 *field_str(const u8 *json, u32 len, const char *key, u32 *out_n) {
    const u8 *p = find_key(json, json + len, key);
    if (!p) return 0;
    while (p < json + len && (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')) p++;
    return json_str(p, json + len, out_n);
}

static u8 *artist_str(const u8 *json, u32 len, u32 *out_n) {
    const u8 *p = find_key(json, json + len, "artist");
    const u8 *end = json + len;
    u8 *out;
    u32 n = 0, cap = 256, sn = 0, depth = 0, count = 0;
    if (!p) return 0;
    out = alloc(cap);
    if (!out) return 0;
    for (; p < end; p++) {
        if (*p == '[') depth++;
        else if (*p == ']') {
            if (depth == 0) break;
            depth--;
            if (depth == 0) break;
        } else if (*p == '"' && depth >= 2) {
            u8 *s = json_str(p, end, &sn);
            if (s && sn) {
                if (n + sn + 2 > cap) {
                    freep(s);
                    break;
                }
                if (count++) out[n++] = '/';
                copyb(out + n, s, sn);
                n += sn;
            }
            freep(s);
            while (p < end && *p != '"') p++;
            if (p < end) p++;
            while (p < end && *p != '"') p++;
        }
    }
    if (!n) { freep(out); return 0; }
    out[n] = 0;
    *out_n = n;
    return out;
}

static int b64val(u8 c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '+') return 62;
    if (c == '/') return 63;
    return -1;
}

static u8 *b64dec(const u8 *in, u32 n, u32 *out_n) {
    u8 *out = alloc((n / 4 + 1) * 3);
    u32 i, o = 0;
    if (!out) return 0;
    for (i = 0; i + 3 < n; i += 4) {
        int a = b64val(in[i]), b = b64val(in[i + 1]);
        int c = in[i + 2] == '=' ? -2 : b64val(in[i + 2]);
        int d = in[i + 3] == '=' ? -2 : b64val(in[i + 3]);
        if (a < 0 || b < 0 || c < -2 || d < -2) break;
        out[o++] = (u8)((a << 2) | (b >> 4));
        if (c >= 0) out[o++] = (u8)((b << 4) | (c >> 2));
        if (d >= 0 && c >= 0) out[o++] = (u8)((c << 6) | d);
    }
    *out_n = o;
    return out;
}

static void parse_meta(u8 *meta, u32 meta_len, TagInfo *t) {
    static const char pref[] = "163 key(Don't modify):";
    u32 pn = sizeof(pref) - 1, dec_n = 0, plain_n = 0;
    u8 *dec = 0, *plain = 0, *json;
    if (meta_len <= pn) return;
    xorb(meta, meta_len, 0x63);
    if (!starts(meta, meta_len, pref)) return;
    dec = b64dec(meta + pn, meta_len - pn, &dec_n);
    if (!dec) return;
    if (aes_ecb_dec(dec, dec_n, META_KEY, &plain, &plain_n) && plain_n > 6) {
        json = plain;
        if (starts(json, plain_n, "music:")) { json += 6; plain_n -= 6; }
        t->title = field_str(json, plain_n, "musicName", &t->title_n);
        t->album = field_str(json, plain_n, "album", &t->album_n);
        t->artist = artist_str(json, plain_n, &t->artist_n);
    }
    freep(plain);
    freep(dec);
}

static void be32(u8 *p, u32 v) {
    p[0] = (u8)(v >> 24); p[1] = (u8)(v >> 16); p[2] = (u8)(v >> 8); p[3] = (u8)v;
}

static void sync32(u8 *p, u32 v) {
    p[0] = (u8)((v >> 21) & 0x7f); p[1] = (u8)((v >> 14) & 0x7f); p[2] = (u8)((v >> 7) & 0x7f); p[3] = (u8)(v & 0x7f);
}

static u32 u16n(const u8 *s, u32 n) {
    u32 i = 0, out = 0;
    while (i < n) {
        u8 c = s[i++];
        if ((c & 0xe0) == 0xc0 && i < n) i++;
        else if ((c & 0xf0) == 0xe0 && i + 1 < n) i += 2;
        out += 2;
    }
    return out;
}

static u32 w16(u8 *o, const u8 *s, u32 n) {
    u32 i = 0, out = 0, cp;
    while (i < n) {
        u8 c = s[i++];
        if ((c & 0xe0) == 0xc0 && i < n) {
            cp = ((u32)(c & 0x1f) << 6) | (s[i++] & 0x3f);
        } else if ((c & 0xf0) == 0xe0 && i + 1 < n) {
            cp = ((u32)(c & 0x0f) << 12) | ((u32)(s[i] & 0x3f) << 6) | (s[i + 1] & 0x3f);
            i += 2;
        } else {
            cp = c;
        }
        o[out++] = (u8)cp;
        o[out++] = (u8)(cp >> 8);
    }
    return out;
}

static u32 frame_text(u8 *o, const char *id, const u8 *s, u32 n) {
    u32 wn;
    if (!s || !n) return 0;
    wn = u16n(s, n);
    o[0] = id[0]; o[1] = id[1]; o[2] = id[2]; o[3] = id[3];
    be32(o + 4, wn + 3);
    o[8] = o[9] = 0;
    o[10] = 1;
    o[11] = 0xff;
    o[12] = 0xfe;
    w16(o + 13, s, n);
    return wn + 13;
}

static u32 frame_apic(u8 *o, const u8 *img, u32 n) {
    const char *mime = (n > 4 && img[0] == 0x89 && img[1] == 'P') ? "image/png" : "image/jpeg";
    u32 ml = 0, i, sz;
    if (!img || !n) return 0;
    while (mime[ml]) ml++;
    sz = 1 + ml + 1 + 1 + 1 + n;
    o[0] = 'A'; o[1] = 'P'; o[2] = 'I'; o[3] = 'C';
    be32(o + 4, sz);
    o[8] = o[9] = 0;
    o[10] = 3;
    for (i = 0; i < ml; i++) o[11 + i] = (u8)mime[i];
    o[11 + ml] = 0;
    o[12 + ml] = 3;
    o[13 + ml] = 0;
    copyb(o + 14 + ml, img, n);
    return sz + 10;
}

static u8 *make_id3(TagInfo *t, u32 *tag_n) {
    u32 cap = 10 + 128 + (t->title_n + t->artist_n + t->album_n) * 2 + t->cover_n;
    u8 *tag = alloc(cap), *p;
    u32 n = 10, fs;
    if (!tag) return 0;
    tag[0] = 'I'; tag[1] = 'D'; tag[2] = '3'; tag[3] = 3; tag[4] = 0; tag[5] = 0;
    n += frame_text(tag + n, "TIT2", t->title, t->title_n);
    n += frame_text(tag + n, "TPE1", t->artist, t->artist_n);
    n += frame_text(tag + n, "TALB", t->album, t->album_n);
    n += frame_apic(tag + n, t->cover, t->cover_n);
    if (n == 10) { freep(tag); return 0; }
    sync32(tag + 6, n - 10);
    *tag_n = n;
    return tag;
}
#endif

static const char *detect_ext(const u8 *p, u32 n) {
    if (n >= 4 && p[0] == 'f' && p[1] == 'L' && p[2] == 'a' && p[3] == 'C') return "flac";
    if (n >= 3 && p[0] == 'I' && p[1] == 'D' && p[2] == '3') return "mp3";
    if (n >= 2 && p[0] == 0xff && (p[1] & 0xe0) == 0xe0) return "mp3";
    if (n >= 8 && p[4] == 'f' && p[5] == 't' && p[6] == 'y' && p[7] == 'p') return "m4a";
    return "bin";
}

static u32 wlen(const WCHAR *s) {
    u32 n = 0;
    while (s[n]) n++;
    return n;
}

static WCHAR *make_out_path(const WCHAR *input, const char *ext) {
    u32 len = wlen(input), i, slash = 0xffffffff, dot = 0xffffffff, base_len, ext_len = 0;
    WCHAR *out;
    while (ext[ext_len]) ext_len++;
    for (i = 0; i < len; i++) {
        if (input[i] == L'\\' || input[i] == L'/') slash = i;
        if (input[i] == L'.') dot = i;
    }
    if (dot == 0xffffffff || (slash != 0xffffffff && dot < slash)) dot = len;
    base_len = dot;
    out = (WCHAR *)HeapAlloc(GetProcessHeap(), 0, (base_len + 1 + ext_len + 1) * sizeof(WCHAR));
    if (!out) return 0;
    for (i = 0; i < base_len; i++) out[i] = input[i];
    out[base_len] = L'.';
    for (i = 0; i < ext_len; i++) out[base_len + 1 + i] = (WCHAR)ext[i];
    out[base_len + 1 + ext_len] = 0;
    return out;
}

static int convert(const WCHAR *in_path, const WCHAR *out_arg) {
    u8 *file = 0, *key_block = 0, *key_plain = 0, *audio = 0;
#ifdef NCMTAGS
    u8 *meta_block = 0, *id3 = 0;
    u32 id3_len = 0;
    TagInfo tags;
#endif
    u32 file_len = 0, pos = 0, key_len = 0, key_plain_len = 0, meta_len = 0, img_len = 0, audio_len = 0;
    u8 keybox[256];
    const char *ext;
    WCHAR *out_path = 0;
    int ok = 0;
#ifdef NCMTAGS
    tags.title = tags.artist = tags.album = 0;
    tags.title_n = tags.artist_n = tags.album_n = 0;
    tags.cover = 0;
    tags.cover_n = 0;
#endif

    if (!read_all(in_path, &file, &file_len)) { LOGA("read failed\n"); goto done; }
    if (file_len < 32 || !eq8(file, NCM_MAGIC)) { LOGA("not ncm\n"); goto done; }
    pos = 10;

    if (pos + 4 > file_len) goto bad;
    key_len = rd32(file + pos); pos += 4;
    if (key_len == 0 || pos + key_len > file_len) goto bad;
    key_block = alloc(key_len);
    if (!key_block) goto done;
    copyb(key_block, file + pos, key_len); pos += key_len;
    xorb(key_block, key_len, 0x64);
    if (!aes_ecb_dec(key_block, key_len, CORE_KEY, &key_plain, &key_plain_len)) goto bad;
    if (key_plain_len <= 17) goto bad;
    build_keybox(key_plain + 17, key_plain_len - 17, keybox);

    if (pos + 4 > file_len) goto bad;
    meta_len = rd32(file + pos); pos += 4;
    if (pos + meta_len > file_len) goto bad;
#ifdef NCMTAGS
    if (meta_len) {
        meta_block = alloc(meta_len);
        if (!meta_block) goto done;
        copyb(meta_block, file + pos, meta_len);
        parse_meta(meta_block, meta_len, &tags);
    }
#endif
    pos += meta_len;

    if (pos + 13 > file_len) goto bad;
    pos += 4;
    pos += 5;
    img_len = rd32(file + pos); pos += 4;
    if (pos + img_len > file_len) goto bad;
#ifdef NCMTAGS
    if (img_len) {
        tags.cover = file + pos;
        tags.cover_n = img_len;
    }
#endif
    pos += img_len;

    audio_len = file_len - pos;
    audio = alloc(audio_len);
    if (!audio) goto done;
    copyb(audio, file + pos, audio_len);
    decrypt_audio(audio, audio_len, keybox);

    ext = detect_ext(audio, audio_len);
    out_path = out_arg ? (WCHAR *)out_arg : make_out_path(in_path, ext);
    if (!out_path) goto done;
#ifdef NCMTAGS
    if (ext[0] == 'm' && ext[1] == 'p' && ext[2] == '3') {
        id3 = make_id3(&tags, &id3_len);
    }
    if (id3) {
        if (!write_two(out_path, id3, id3_len, audio, audio_len)) { LOGA("write failed\n"); goto done; }
    } else
#endif
    if (!write_all(out_path, audio, audio_len)) { LOGA("write failed\n"); goto done; }
    LOGA("ok\n");
    ok = 1;
    goto done;

bad:
    LOGA("bad ncm\n");
done:
    if (!out_arg) freep(out_path);
#ifdef NCMTAGS
    freep(id3);
    freep(tags.title);
    freep(tags.artist);
    freep(tags.album);
    freep(meta_block);
#endif
    freep(audio);
    freep(key_plain);
    freep(key_block);
    freep(file);
    return ok;
}

static WCHAR *skip_ws(WCHAR *p) {
    while (*p == L' ' || *p == L'\t') p++;
    return p;
}

static WCHAR *next_arg(WCHAR **cursor) {
    WCHAR *p = skip_ws(*cursor);
    WCHAR *start;
    if (!*p) return 0;
    if (*p == L'"') {
        p++;
        start = p;
        while (*p && *p != L'"') p++;
        if (*p) *p++ = 0;
    } else {
        start = p;
        while (*p && *p != L' ' && *p != L'\t') p++;
        if (*p) *p++ = 0;
    }
    *cursor = p;
    return start;
}

void mainCRTStartup(void) {
#ifndef NCMGUI
    WCHAR *cmd = GetCommandLineW();
    WCHAR *p = cmd;
    WCHAR *exe, *in, *out;
    int code;
    exe = next_arg(&p);
    (void)exe;
    in = next_arg(&p);
    out = next_arg(&p);
    if (!in) {
        outa("usage: ncmmini.exe input.ncm [output]\n");
        ExitProcess(1);
    }
    code = convert(in, out) ? 0 : 2;
    ExitProcess((UINT)code);
#else
    static OPENFILENAMEW ofn;
    static WCHAR file[32768];
    static WCHAR filter[] = L"NCM\0*.ncm\0\0";
    int ok;

    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = 0;
    ofn.lpstrFilter = filter;
    ofn.lpstrFile = file;
    ofn.nMaxFile = sizeof(file) / sizeof(file[0]);
    ofn.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_EXPLORER;
    ofn.lpstrTitle = L"NCM";

    if (!GetOpenFileNameW(&ofn)) {
        ExitProcess(0);
    }

    ok = convert(file, 0);
    MessageBoxW(0,
        ok ? L"OK" : L"FAIL",
        L"NCM",
        ok ? MB_OK | MB_ICONINFORMATION : MB_OK | MB_ICONERROR);
    ExitProcess(ok ? 0 : 2);
#endif
}

*编译器
@echo off
setlocal
set "ROOT=%~dp0"
set "VC=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars32.bat"
if not exist "%VC%" goto missing
call "%VC%" >nul
cl /nologo /utf-8 /O1 /Os /GS- /Gy /Gw /DNCMGUI /DNCMTAGS /TC "%ROOT%ncmmini.c" /Fo"%ROOT%ncmmini.obj" /Fe"%ROOT%NCMConverter.exe" /link /NODEFAULTLIB /ENTRY:mainCRTStartup /SUBSYSTEM:WINDOWS /OPT:REF /OPT:ICF /MERGE:.rdata=.text kernel32.lib user32.lib comdlg32.lib bcrypt.lib
if errorlevel 1 exit /b 1
del "%ROOT%ncmmini.obj" 2>nul
dir "%ROOT%NCMConverter.exe"
exit /b 0
:missing
echo vcvars32.bat not found
exit /b 1

*我自己的插件示例（Nightmare）
~~~
**现在，请将c源码迁移为python语言，并同步nightmare插件的注释风格生成TryX（1），包含四个必要的插件文件，并先给出免责文案，我去创建项目。
-------------------------------------------------------------try3
import { defineAction, groupAction, registerActions, f } from '../action-kit';
import type { ApiHandler, ApiActionContext } from '../api-handler';
import { RETCODE, failedResponse, okResponse } from '../types';

export const actions = [
  groupAction({
    name: 'upload_group_file',
    summary: '上传群文件',
    returns: '{ file_id: string }',
    // `folder` / `folder_id` are two aliases for one target dir; the first
    // non-empty wins, else '/'. Both default '' so the `||` chain matches the
    // legacy `asString(folder) || asString(folder_id) || '/'`.
    params: {
      file: f.string({ allowEmpty: false }),
      name: f.string().default(''),
      folder: f.string().default(''),
      folder_id: f.string().default(''),
      upload_file: f.bool().default(true),
    },
    run: async (p, ctx) => {
      const folderId = p.folder || p.folder_id || '/';
      const result = await ctx.bridge.apis.groupFile.upload(p.group_id, p.file, p.name, folderId, p.upload_file);
      return okResponse({ file_id: result.fileId });
    },
  }),

  defineAction({
    name: 'upload_private_file',
    summary: '上传私聊文件',
    returns: '{ file_id: string }',
    params: {
      user_id: f.uint(),
      file: f.string({ allowEmpty: false }),
      name: f.string().default(''),
      upload_file: f.bool().default(true),
    },
    run: async (p, ctx) => {
      const result = await ctx.bridge.apis.groupFile.uploadPrivate(p.user_id, p.file, p.name, p.upload_file);
      return okResponse({ file_id: result.fileId });
    },
  }),

  groupAction({
    name: 'get_group_file_url',
    summary: '获取群文件下载链接',
    readOnly: true,
    returns: '{ url: string }',
    // busid: legacy `asNumber(busid) || 102` mapped absent/0/invalid → 102.
    // f.int({min:0}).default(102) keeps absent → 102, but a present 0 now
    // stays 0 and a non-numeric busid is now rejected (BAD_REQUEST) instead
    // of silently becoming 102.
    params: { file_id: f.string({ allowEmpty: false }), busid: f.int({ min: 0 }).default(102) },
    run: async (p, ctx) => {
      return okResponse({ url: await ctx.bridge.apis.groupFile.getUrl(p.group_id, p.file_id, p.busid) });
    },
  }),

  groupAction({
    name: 'get_group_root_files',
    summary: '获取群根目录文件列表',
    readOnly: true,
    run: async (p, ctx) => {
      return okResponse(await ctx.getGroupFiles(p.group_id, '/'));
    },
  }),

  groupAction({
    name: 'get_group_files_by_folder',
    summary: '获取群子目录文件列表',
    readOnly: true,
    // folder_id / folder are aliases; first non-empty wins, else '/'.
    params: { folder_id: f.string().default(''), folder: f.string().default('') },
    run: async (p, ctx) => {
      const folderId = p.folder_id || p.folder || '/';
      return okResponse(await ctx.getGroupFiles(p.group_id, folderId));
    },
  }),

  groupAction({
    name: 'delete_group_file',
    summary: '删除群文件',
    params: { file_id: f.string({ allowEmpty: false }) },
    run: async (p, ctx) => {
      await ctx.bridge.apis.groupFile.delete(p.group_id, p.file_id);
      return okResponse();
    },
  }),

  groupAction({
    name: 'move_group_file',
    summary: '移动群文件',
    params: {
      file_id: f.string({ allowEmpty: false }),
      parent_directory: f.string({ allowEmpty: false }),
      target_directory: f.string({ allowEmpty: false }),
    },
    run: async (p, ctx) => {
      await ctx.bridge.apis.groupFile.move(p.group_id, p.file_id, p.parent_directory, p.target_directory);
      return okResponse();
    },
  }),

  // rename_group_file — 0x6D6_4。NapCat 入参：file_id + current_parent_directory
  // （文件当前所在目录）+ new_name。SnowLuma 的 file_id 即原始 fileId，无需 UUID 解码。
  groupAction({
    name: 'rename_group_file',
    summary: '重命名群文件',
    params: {
      file_id: f.string({ allowEmpty: false }),
      current_parent_directory: f.string().default('/'),
      new_name: f.string({ allowEmpty: false }),
    },
    run: async (p, ctx) => {
      await ctx.bridge.apis.groupFile.rename(p.group_id, p.file_id, p.current_parent_directory || '/', p.new_name);
      // {ok:true} 刻意对齐 NapCat RenameGroupFile 的返回体，偏离 SnowLuma 同类
      // 文件写操作（move/delete 返回空 data）——为 NapCat 客户端 drop-in 兼容。
      return okResponse({ ok: true });
    },
  }),

  groupAction({
    name: 'create_group_file_folder',
    summary: '创建群文件夹',
    params: { name: f.string({ allowEmpty: false }), parent_id: f.string().default('/') },
    run: async (p, ctx) => {
      await ctx.bridge.apis.groupFile.createFolder(p.group_id, p.name, p.parent_id || '/');
      return okResponse();
    },
  }),

  groupAction({
    name: 'delete_group_file_folder',
    summary: '删除群文件夹',
    params: { folder_id: f.string({ allowEmpty: false }) },
    run: async (p, ctx) => {
      await ctx.bridge.apis.groupFile.deleteFolder(p.group_id, p.folder_id);
      return okResponse();
    },
  }),

  groupAction({
    name: 'rename_group_file_folder',
    summary: '重命名群文件夹',
    // new_folder_name / name are aliases; first non-empty wins and must be
    // non-empty (legacy `asString(new_folder_name) || asString(name)` + `!newName`).
    params: { folder_id: f.string({ allowEmpty: false }), new_folder_name: f.string().default(''), name: f.string().default('') },
    run: async (p, ctx) => {
      const newName = p.new_folder_name || p.name;
      if (!newName) {
        return failedResponse(RETCODE.BAD_REQUEST, 'group_id, folder_id and new_folder_name are required');
      }
      await ctx.bridge.apis.groupFile.renameFolder(p.group_id, p.folder_id, newName);
      return okResponse();
    },
  }),

  defineAction({
    name: 'get_private_file_url',
    summary: '获取私聊文件下载链接',
    readOnly: true,
    returns: '{ url: string }',
    params: {
      user_id: f.uint(),
      file_id: f.string({ allowEmpty: false }),
      file_hash: f.string({ allowEmpty: false }),
    },
    run: async (p, ctx) => {
      return okResponse({ url: await ctx.bridge.apis.groupFile.getPrivateUrl(p.user_id, p.file_id, p.file_hash) });
    },
  }),
];

export function register(h: ApiHandler, ctx: ApiActionContext): void {
  registerActions(h, ctx, actions);
}
这是snowluma的group-file.ts文件，请使用其中的方法，完善并努力整个try3，我将在稍后添加除了snowluma的另一个接口napcat的使用方法
-------------------------------------------------------------try5
06-25 19:46:55 [所见] [1m的喂鸽小屋]1m:[文件] onoken,木下珠子 - Finale our hope „Carpe-Diem“ (feat. 木下珠子).ncm，大小: 6494842，链接: https://gzc-download.ftn.qq.com/ftn_handler/597ED5D11ACF2DF714E7E1145087F950225FD3B95BCB523EDBCBFB9458CC456B7A5EE8AD3D8979397EC20B7A5F2841504020968A5FF3D626302101EA882B8806/?fname=/c5cc8339-c6df-48f7-a5e4-7eeccb03a2fa
06-25 19:46:55 [插件清单校验] Manifest 校验失败 [SengokuCola.maimai-birdwatching-plugin]: 共 3 项，存在未声明字段: homepage_url；存在未声明字段: repository_url；存在未声明字段: categories
06-25 19:46:55 [插件清单校验] Manifest 校验失败 [/MaiMBot/plugins/a-dawn.a-memorix]: 共 1 项，缺少 _manifest.json
06-25 19:46:55 [插件清单校验] Manifest 校验失败 [/MaiMBot/plugins/goodnight_sleep_manager]: 共 1 项，缺少 _manifest.json
06-25 19:46:55 [插件清单校验] Manifest 校验失败 [small_sunshine.date-aware-plugin]: 共 2 项，存在未声明字段: keywords；存在未声明字段: categories
06-25 19:47:25 [maisaka_reasoning_engine] [1m的喂鸽小屋] 本轮思考前已刷新 28 条视觉占位历史消息
06-25 19:47:33 [maisaka_chat_loop] Maisaka KV cache usage - request_kind=timing_gate, hit_tokens=640, miss_tokens=19030, hit_rate=3.25%, prompt_tokens=19670
╭────────────────────────────── MaiSaka 循环 [1] ──────────────────────────────╮
│ 聊天流名称：1m的喂鸽小屋                                                     │
│ 聊天流ID：84a5aacc340b3a1600a53be855831312                                   │
│ 当前回复频率：0.500（50.0%）                                                 │
│ ╭────────────────────────────── Timing Gate ───────────────────────────────╮ │
│ │ 请求模型：deepseek-v4-flash                                              │ │
│ │ 本次请求token消耗：19.7k                                                 │ │
│ │ ╭────────────── MaiSaka 大模型请求 - Timing Gate 子代理 ───────────────╮ │ │
│ │ │ html预览：logs/maisaka_prompt/timing_gate/qq_group_453179577/1782388 │ │ │
│ │ │ 053302.html 在浏览器打开 Prompt                                      │ │ │
│ │ │ 结构化记录：logs/maisaka_prompt/timing_gate/qq_group_453179577/17823 │ │ │
│ │ │ 88053302.json 点击打开 JSON 记录                                     │ │ │
│ │ ╰─ 实际发送 512 条消息|消息 512 条|tool 0 条|cache_window 1024->2048  ─╯ │ │
│ │ ╭──────────────────────────── Maisaka 返回 ────────────────────────────╮ │ │
│ │ │ 当前最新的消息是1m在19:46:55发了一个ncm文件（onoken的《Finale our    │ │ │
│ │ │ hope》），距离现在不到1分钟。从上下文看，这很可能是之前提到的"工作来 │ │ │
│ │ │ 了"相关的歌曲文件。1m还没有对文件做出任何说明或@混色七，可能正在编辑 │ │ │
│ │ │ 后续消息，也可能只是先扔文件进群。                                   │ │ │
│ │ │                                                                      │ │ │
│ │ │ 这种情况下我选择适当等待，让用户先把话说完或说明意图。               │ │ │
│ │ ╰──────────────────────────────────────────────────────────────────────╯ │ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
│ ╭─────────────────────────── Timing Tool · wait ───────────────────────────╮ │
│ │ - wait [成功]: 当前对话循环进入等待状态，将固定等待 60                   │ │
│ │ 秒；期间收到的新消息不会提前打断本次等待。                               │ │
│ │ 调用ID：call_00_hVFK9OOA2C9fBnw9Bx8F7279                                 │ │
│ │ 执行耗时：0.0 ms                                                         │ │
│ │ ╭────────────────────────────── 工具参数 ──────────────────────────────╮ │ │
│ │ │ {                                                                    │ │ │
│ │ │     'seconds': 60                                                    │ │ │
│ │ │ }                                                                    │ │ │
│ │ ╰──────────────────────────────────────────────────────────────────────╯ │ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
╰─────────── 流程耗时：Timing Gate 12.13 s | visual_refresh 0.12 s ────────────╯
06-25 19:48:38 [maisaka_reasoning_engine] [1m的喂鸽小屋] 等待超时后开始新一轮思考
06-25 19:48:42 [maisaka_chat_loop] Maisaka KV cache usage - request_kind=timing_gate, hit_tokens=19584, miss_tokens=184, hit_rate=99.07%, prompt_tokens=19768
╭────────────────────────────── MaiSaka 循环 [2] ──────────────────────────────╮
│ 聊天流名称：1m的喂鸽小屋                                                     │
│ 聊天流ID：84a5aacc340b3a1600a53be855831312                                   │
│ 当前回复频率：0.500（50.0%）                                                 │
│ ╭────────────────────────────── Timing Gate ───────────────────────────────╮ │
│ │ 请求模型：deepseek-v4-flash                                              │ │
│ │ 本次请求token消耗：19.8k                                                 │ │
│ │ ╭────────────── MaiSaka 大模型请求 - Timing Gate 子代理 ───────────────╮ │ │
│ │ │ html预览：logs/maisaka_prompt/timing_gate/qq_group_453179577/1782388 │ │ │
│ │ │ 122662.html 在浏览器打开 Prompt                                      │ │ │
│ │ │ 结构化记录：logs/maisaka_prompt/timing_gate/qq_group_453179577/17823 │ │ │
│ │ │ 88122662.json 点击打开 JSON 记录                                     │ │ │
│ │ ╰─ 实际发送 513 条消息|消息 513 条|tool 0 条|cache_window 1024->2048  ─╯ │ │
│ │ ╭──────────────────────────── Maisaka 返回 ────────────────────────────╮ │ │
│ │ │ 最近一条消息是1m在19:46:55上传了一个ncm文件（onoken的《Finale our    │ │ │
│ │ │ hope》），至今约2分钟。从上下文来看，这个文件应该是之前提到的"工作来 │ │ │
│ │ │ 了"相关的歌曲文件，1m之前还提到过这个词作相关的task。                │ │ │
│ │ │                                                                      │ │ │
│ │ │ 1m刚发完文件还没有说明意图或@我，可能正在编辑后续消息，我选择继续等  │ │ │
│ │ │ 待，让他先把话说完。                                                 │ │ │
│ │ ╰──────────────────────────────────────────────────────────────────────╯ │ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
│ ╭─────────────────────────── Timing Tool · wait ───────────────────────────╮ │
│ │ - wait [成功]: 当前对话循环进入等待状态，将固定等待 60                   │ │
│ │ 秒；期间收到的新消息不会提前打断本次等待。                               │ │
│ │ 调用ID：call_00_NDWHzCIKOxybVEOykuuJ8133                                 │ │
│ │ 执行耗时：0.0 ms                                                         │ │
│ │ ╭────────────────────────────── 工具参数 ──────────────────────────────╮ │ │
│ │ │ {                                                                    │ │ │
│ │ │     'seconds': 60                                                    │ │ │
│ │ │ }                                                                    │ │ │
│ │ ╰──────────────────────────────────────────────────────────────────────╯ │ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
╰──────────── 流程耗时：Timing Gate 5.18 s | visual_refresh 0.05 s ────────────╯

收到ncm文件后并未开始解码。请完成：1.添加收到文件后的日志。2。将WebUI的网关设置适配器、随机提示语改为下拉菜单式，其中网关可选SL或Napcat。3.隐藏测试文件设置，改为测试命令选项，能在此开关是否启用/ncm命令，/ncm将会将解码后的测试文件发送给测试账号。4.添加测试账号选项，/ncm的命令将只对此用户生效。5.隐藏缓存清理设置，改为自动在发送给用户解码文件后删除所有缓存。请跟据需要修改、增添程序逻辑，生成tryX