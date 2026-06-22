"""GLSL shader sources for the 3D star rendering engine."""

STAR_VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in float aMag;
layout(location = 2) in vec3 aColor;
layout(location = 3) in float aScintPhase;

uniform mat4 uProjection;
uniform mat4 uView;
uniform float uPointScale;
uniform float uTime;

out float vMag;
out vec3 vColor;
out float vScint;

void main() {
    vec4 pos = uProjection * uView * vec4(aPos, 1.0);
    gl_Position = pos;

    float size = max(2.0, (8.0 - aMag * 0.6) * uPointScale);
    float scint = 0.7 + 0.3 * sin(uTime * 2.0 + aScintPhase);
    vScint = scint;
    gl_PointSize = size * scint;

    vMag = aMag;
    vColor = aColor;
}
"""

STAR_FRAGMENT_SHADER = """
#version 330 core
in float vMag;
in vec3 vColor;
in float vScint;

out vec4 FragColor;

void main() {
    vec2 coord = gl_PointCoord - vec2(0.5);
    float dist = length(coord);
    float sigma = 0.28;
    float gaussian = exp(-(dist * dist) / (2.0 * sigma * sigma));
    gaussian = max(gaussian - exp(-0.25 / (2.0 * sigma * sigma)), 0.0) / (1.0 - exp(-0.25 / (2.0 * sigma * sigma)));
    float alpha = gaussian * vScint;
    if (alpha < 0.01) discard;
    FragColor = vec4(vColor * (0.8 + 0.2 * vScint), alpha);
}
"""

SKYBOX_VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec3 aPos;
out vec3 vTexCoord;
uniform mat4 uProjection;
uniform mat4 uView;

void main() {
    vec4 pos = uProjection * uView * vec4(aPos, 1.0);
    gl_Position = pos.xyww;
    vTexCoord = aPos;
}
"""

SKYBOX_FRAGMENT_SHADER = """
#version 330 core
in vec3 vTexCoord;
out vec4 FragColor;

uniform vec3 uSkyColor;
uniform vec3 uHorizonColor;
uniform float uMilkyWayAlpha;
uniform float uSunAltitude;

layout(std140) uniform GalaxySampler {
    vec4 galaxyPoints[1024];
};

vec3 hash33(vec3 p) {
    p = fract(p * vec3(443.8975, 397.2973, 491.1871));
    p += dot(p, p.yxz + 19.19);
    return fract((p.xxy + p.yxx) * p.zyx);
}

float galaxy_noise(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float n = dot(i, vec3(1.0, 57.0, 113.0));
    vec4 d = vec4(
        hash33(i + vec3(0,0,0)).x,
        hash33(i + vec3(1,0,0)).x,
        hash33(i + vec3(0,1,0)).x,
        hash33(i + vec3(0,0,1)).x
    );
    return mix(mix(d.x, d.y, f.x), mix(d.z, d.w, f.x), f.y);
}

float galaxy_density(vec3 dir) {
    float theta = atan(dir.z, dir.x);
    float phi = asin(clamp(dir.y, -1.0, 1.0));
    float galactic_lat = abs(phi);
    float galactic_lon = theta;

    float disk = exp(-galactic_lat * 18.0) * (0.6 + 0.4 * sin(galactic_lon * 2.0 + 0.5));
    float bulge = exp(-galactic_lat * 8.0) * exp(-pow(abs(galactic_lon - 3.14) * 0.3, 2.0)) * 0.5;
    float dust = galaxy_noise(dir * 4.0) * 0.15;
    float detail = galaxy_noise(dir * 32.0) * 0.05;
    float bands = abs(sin(galactic_lat * 40.0 + galactic_lon * 3.0)) * 0.08;
    float milky = disk + bulge + dust + detail + bands;
    return pow(clamp(milky, 0.0, 1.0), 0.7);
}

vec3 atmospheric_color(float alt_deg) {
    float a = clamp((alt_deg + 5.0) / 95.0, 0.0, 1.0);
    vec3 night = vec3(0.01, 0.01, 0.03);
    vec3 twilight = vec3(0.15, 0.08, 0.20);
    vec3 day = vec3(0.15, 0.25, 0.55);
    vec3 col = mix(night, twilight, smoothstep(0.0, 0.1, a));
    col = mix(col, day, smoothstep(0.1, 0.3, a));
    return col;
}

void main() {
    vec3 dir = normalize(vTexCoord);
    float alt = asin(clamp(dir.y, -1.0, 1.0));
    float alt_deg = degrees(alt);

    vec3 base = atmospheric_color(alt_deg + uSunAltitude * 0.3);

    float sun_angle = degrees(acos(dot(dir, normalize(vec3(0.0, 1.0, -1.0)))));
    float horizon_glow = exp(-sun_angle * 0.05) * max(0.0, uSunAltitude + 5.0) * 0.005;
    base += vec3(1.0, 0.6, 0.2) * horizon_glow;

    float milky = galaxy_density(dir) * uMilkyWayAlpha;
    vec3 milky_color = vec3(0.7, 0.6, 0.5) * milky;
    base += milky_color;

    base = max(base, vec3(0.0));
    base = pow(base, vec3(1.0 / 2.2));

    FragColor = vec4(base, 1.0);
}
"""

BLOOM_VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec2 aPos;
layout(location = 1) in vec2 aTexCoord;
out vec2 vTexCoord;
void main() {
    gl_Position = vec4(aPos, 0.0, 1.0);
    vTexCoord = aTexCoord;
}
"""

BLOOM_FRAGMENT_SHADER = """
#version 330 core
in vec2 vTexCoord;
out vec4 FragColor;
uniform sampler2D uSceneTex;
uniform vec2 uTexelSize;

void main() {
    vec4 color = texture(uSceneTex, vTexCoord);
    vec4 bloom = vec4(0.0);
    float weights[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);
    for (int i = 1; i < 5; i++) {
        bloom += texture(uSceneTex, vTexCoord + vec2(uTexelSize.x * i, 0.0)) * weights[i];
        bloom += texture(uSceneTex, vTexCoord - vec2(uTexelSize.x * i, 0.0)) * weights[i];
    }
    bloom *= weights[0];
    FragColor = color + bloom * 0.5;
}
"""

ATMOSPHERE_VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec3 aPos;
uniform mat4 uProjection;
uniform mat4 uView;
void main() {
    gl_Position = uProjection * uView * vec4(aPos, 1.0);
}
"""

ATMOSPHERE_FRAGMENT_SHADER = """
#version 330 core
out vec4 FragColor;
uniform vec3 uSunDir;
uniform vec3 uViewPos;

void main() {
    vec3 sun_dir = normalize(uSunDir);
    float sun_alt = sun_dir.y;
    vec3 color;
    if (sun_alt > 0.1) {
        color = vec3(0.15, 0.25, 0.55);
    } else if (sun_alt > -0.1) {
        float t = (sun_alt + 0.1) / 0.2;
        color = mix(vec3(0.05, 0.02, 0.10), vec3(0.15, 0.25, 0.55), t);
    } else {
        color = vec3(0.01, 0.01, 0.03);
    }
    FragColor = vec4(color, 1.0);
}
"""
