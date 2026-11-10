"""fp64 Warp reduced-model design/UQ/Tape kernels. Shared exactly by CUDA and CPU.
Surrogate is PhysicsNeMo trained on independent Warp finite-volume labels, tabulated in a,b.
Panel mass uses exact circular 8/7-mm tube annulus; coolant head stays conservatively inherited.
"""
import warp as wp
P_NAMES = ['static', 'base_sum', 'core0', 'ram0', 'prop0', 'radA0', 'arrA0', 'arr_ram', 'dragC', 'dv0', 'isp_g', 'arr_kg_m2', 'harness0', 'pcdu0', 'struct0', 'deploy0', 'bol', 'pump_peak', 'pump_nom', 'qenv', 'yoke', 'tube_blk', 'safe', 'switch', 'heater4_perpanel', 'swivel_perpanel', 'insert_perpanel', 'acc_kgL', 'specific_expansion', 'racktrunk_fluid', 'hdrfluid_perpanel', 'packAmax', 'gpu_goal', 'inlet_goal', 'packNmax', 'cp_nom','mu_nom','kf_nom','cp_pk','mu_pk','kf_pk','env_IR_unit','env_albedo','peak_power_acceptance_W']

@wp.func
def curve(a: wp.array(dtype=wp.float64), n: wp.float64):
    x = wp.clamp(n - wp.float64(112.0), wp.float64(0.0), wp.float64(48.0))
    i = wp.min(wp.int32(wp.floor(x)), 47)
    f = x - wp.float64(i)
    return a[i] * (wp.float64(1.0) - f) + a[i + 1] * f

@wp.func
def ef(a: wp.float64, b: wp.float64, tab: wp.array(dtype=wp.float64)):
    z = (wp.log(wp.clamp(a, wp.float64(0.0005), wp.float64(1.5))) - wp.float64(-7.600902459542082)) / wp.float64(0.015637436655566887)
    i = wp.min(wp.int32(wp.floor(z)), 511)
    f = z - wp.float64(i)
    y = (wp.clamp(b, wp.float64(0.3), wp.float64(0.76)) - wp.float64(0.3)) / wp.float64(0.00359375)
    j = wp.min(wp.int32(wp.floor(y)), 127)
    g = y - wp.float64(j)
    return (wp.float64(1.0) - f) * ((wp.float64(1.0) - g) * tab[i * 129 + j] + g * tab[i * 129 + j + 1]) + f * ((wp.float64(1.0) - g) * tab[(i + 1) * 129 + j] + g * tab[(i + 1) * 129 + j + 1])

@wp.func
def flux(T: wp.float64, E: wp.float64, S: wp.float64, L: wp.float64, t: wp.float64, k: wp.float64, tab: wp.array(dtype=wp.float64)):
    aa = wp.float64(2.0) * E * wp.float64(5.670374419e-08) * L * L * T * T * T / (k * t)
    b = S / T
    eta = (L * ef(aa, b, tab) + wp.float64(0.004)) / (L + wp.float64(0.004))
    return wp.float64(2.0) * E * wp.float64(5.670374419e-08) * (T * T * T * T - S * S * S * S) * eta

@wp.func
def qmean(T: wp.float64, E: wp.float64, S: wp.float64, L: wp.float64, t: wp.float64, k: wp.float64, rise: wp.float64, tab: wp.array(dtype=wp.float64)):
    return (flux(T, E, S, L, t, k, tab) + wp.float64(4.0) * flux(T + rise * wp.float64(0.5), E, S, L, t, k, tab) + flux(T + rise, E, S, L, t, k, tab)) / wp.float64(6.0)

@wp.func
def root(Q: wp.float64, A: wp.float64, E: wp.float64, S: wp.float64, L: wp.float64, t: wp.float64, k: wp.float64, rise: wp.float64, tab: wp.array(dtype=wp.float64)):
    T = wp.float64(365.0)
    for it in range(12):
        f = A * qmean(T, E, S, L, t, k, rise, tab) - Q
        d = A * (qmean(T + wp.float64(0.02), E, S, L, t, k, rise, tab) - qmean(T - wp.float64(0.02), E, S, L, t, k, rise, tab)) / wp.float64(0.04)
        T = wp.clamp(T - f / d, wp.float64(280.0), wp.float64(440.0))
    return T + wp.float64(0.44)

@wp.func
def film_delta(Q:wp.float64,IT:wp.float64,n:wp.float64,L:wp.float64,dt:wp.float64,cp:wp.float64,mu:wp.float64,kf:wp.float64,hscale:wp.float64):
 nt=wp.float64(.3634175776637853)/(wp.float64(2.)*L+wp.float64(.008));cols=wp.ceil(n/wp.float64(10.));mt=IT/(cp*dt*cols*nt);Re=wp.float64(4.)*mt/(wp.float64(.02199114857512855)*mu);Pr=cp*mu/kf
 rr=wp.max(Re,wp.float64(3000.));f=wp.pow(wp.float64(.79)*wp.log(rr)-wp.float64(1.64),wp.float64(-2.));Nu=(f/wp.float64(8.))*(rr-wp.float64(1000.))*Pr/(wp.float64(1.)+wp.float64(12.7)*wp.sqrt(f/wp.float64(8.))*(wp.pow(Pr,wp.float64(.6666666666666666))-wp.float64(1.)))
 blend=wp.clamp((Re-wp.float64(2300.))/wp.float64(700.),wp.float64(0.),wp.float64(1.));Nu=wp.float64(3.66)*(wp.float64(1.)-blend)+Nu*blend;h=Nu*kf/wp.float64(.007)*hscale
 return Q/(n*nt*wp.float64(0.06475513609432353)*h)
@wp.func
def temperatures(n: wp.float64, L: wp.float64, t: wp.float64, eps: wp.float64, Rplate: wp.float64, Hrise: wp.float64, pmad: wp.float64, rackrise: wp.float64, film: wp.float64, envscale: wp.float64, viewscale: wp.float64, pumpscale: wp.float64, k: wp.float64, p: wp.array(dtype=wp.float64), fe: wp.array(dtype=wp.float64), tab: wp.array(dtype=wp.float64), hf:wp.float64, cps:wp.float64, mus:wp.float64):
    E = eps * curve(fe, n) * p[20] * p[21] * viewscale
    S = wp.pow((p[41]*eps+p[42])*envscale / (E * wp.float64(5.670374419e-08)), wp.float64(0.25))
    A = n * wp.float64(1.070119399188782)
    pumps = pumpscale * (wp.float64(20.0) / rackrise) * (wp.float64(20.0) / rackrise)
    Qn = (wp.float64(177000.0) + p[18] * pumps) / pmad
    Qp = (wp.float64(252000.0) + p[17] * pumps) / pmad
    dn = rackrise * Qn / wp.float64(175000.0)
    dp = rackrise * Qp / wp.float64(250000.0)
    sn = root(Qn, A, E, S, L, t, k, dn, tab)+film_delta(Qn,wp.float64(175000.),n,L,rackrise,p[35]*cps,p[36]*mus,p[37],hf)
    sp = root(Qp, A, E, S, L, t, k, dp, tab)+film_delta(Qp,wp.float64(250000.),n,L,rackrise,p[38]*cps,p[39]*mus,p[40],hf)
    plate = Rplate * (wp.float64(0.5) + wp.float64(0.5) / film)
    return wp.vec3d(sn + rackrise * wp.float64(0.5) + wp.float64(1.19) * plate, sn + rackrise * wp.float64(0.5) + wp.float64(0.7) * Hrise, sp + dp)

@wp.func
def radiator_mass(n: wp.float64, L: wp.float64, t: wp.float64):
    pitch = wp.float64(2.0) * L + wp.float64(0.008)
    sheet = wp.float64(2700.0) * t * (wp.float64(2.0) * L) / pitch
    tube = wp.float64(0.03180862561759664) / pitch
    fluid = wp.float64(0.038484510006474966) / pitch
    return n * wp.float64(1.070119399188782) * (sheet + tube + fluid)

@wp.func
def prop(core: wp.float64, ram: wp.float64, p: wp.array(dtype=wp.float64)):
    pr = wp.float64(0.0)
    for i in range(16):
        dry = core - pr
        dv = p[9] + p[8] * ram / (core - wp.float64(0.5) * pr)
        pr = dry * (wp.exp(dv / p[10]) - wp.float64(1.0)) * wp.float64(1.21)
    return pr

@wp.func
def mass(n: wp.float64, L: wp.float64, t: wp.float64, arr: wp.float64, p: wp.array(dtype=wp.float64), cool: wp.array(dtype=wp.float64)):
    nt = wp.float64(0.3634175776637853) / (wp.float64(2.0) * L + wp.float64(0.008))
    rad = radiator_mass(n, L, t)
    inv = p[29] + n * p[30] + n * nt * wp.float64(0.1133214881650662)
    acc = p[27] * inv * p[28]
    hw = p[22] + p[23] + n * (p[24] * nt / wp.float64(4.0) + p[25] + p[26]) + acc
    structure = (p[14] + p[15]) * wp.max(wp.float64(1.0), n / wp.float64(128.0))
    distribution = (p[12] + p[13]) * arr / p[6]
    dry = p[0] + rad + curve(cool, n) + wp.max(wp.float64(90.0), hw) + structure + distribution + arr * p[11]
    dadd = dry - p[1]
    ram = p[3] + (arr - p[6]) * p[7] + n * wp.float64(1.070119399188782) - p[5]
    return dry + prop(p[2] + dadd, ram, p) - p[4]

@wp.kernel
def sweep(p: wp.array(dtype=wp.float64), fe: wp.array(dtype=wp.float64), cool: wp.array(dtype=wp.float64), tab: wp.array(dtype=wp.float64), out: wp.array2d(dtype=wp.float64)):
    i = wp.tid()
    ai = i % 64
    ti = i // 64 % 64
    nti = i // 4096 % 9
    ni = i // 36864
    n = wp.float64(112 + ni)
    nt = wp.float64(6 + nti)
    L = (wp.float64(0.3634175776637853) / nt - wp.float64(0.008)) / wp.float64(2.0)
    t = wp.float64(0.0001) + wp.float64(ti) * wp.float64(6.349206349206349e-06)
    # r11: array grid anchored at the August fixed array (p[31]); peak payload power is an explicit acceptance test.
    arr = p[31] * (wp.float64(1.0) + wp.float64(ai) * wp.float64(0.0006349206349206349))
    # available BOL payload power = array output x PMAD - aux - peak pump; +1e-6 m2 tolerance (pre-existing packing tolerance) expressed in W
    pavail = (arr + wp.float64(1e-06)) * p[16] * wp.float64(0.92) - wp.float64(2000.0) - p[17]
    T = temperatures(n, L, t, wp.float64(0.92), wp.float64(14.22), wp.float64(18.0), wp.float64(0.92), wp.float64(20.0), wp.float64(1.0), wp.float64(1.0), wp.float64(1.0), wp.float64(1.0), wp.float64(167.0), p, fe, tab, wp.float64(1.), wp.float64(1.), wp.float64(1.))
    m = mass(n, L, t, arr, p, cool)
    hard = wp.float64(0.0)
    design = wp.float64(0.0)
    if n <= p[34] and arr <= p[31] + wp.float64(1e-06) and pavail >= p[43] and (m <= wp.float64(3266.6666666666665)) and (T[0] <= wp.float64(370.0)) and (T[2] <= wp.float64(393.0)):
        hard = wp.float64(1.0)
    if hard > wp.float64(0.5) and T[0] <= p[32] and (T[2] <= p[33]):
        design = wp.float64(1.0)
    out[i, 0] = m
    out[i, 1] = T[0]
    out[i, 2] = T[1]
    out[i, 3] = T[2]
    out[i, 4] = n
    out[i, 5] = nt
    out[i, 6] = L
    out[i, 7] = t
    out[i, 8] = arr
    out[i, 9] = hard
    out[i, 10] = design
    out[i, 11] = radiator_mass(n, L, t)

@wp.kernel
def mc(u: wp.array2d(dtype=wp.float64), z: wp.array(dtype=wp.float64), p: wp.array(dtype=wp.float64), fe: wp.array(dtype=wp.float64), tab: wp.array(dtype=wp.float64), out: wp.array2d(dtype=wp.float64)):
    i = wp.tid()
    eps = wp.float64(0.88) + wp.float64(0.08) * u[i, 0]
    R = wp.float64(12.8) + wp.float64(4.3) * u[i, 1]
    H = wp.float64(16.0) + wp.float64(6.0) * u[i, 2]
    pm = wp.float64(0.88) + wp.float64(0.07) * u[i, 3]
    dt = wp.float64(16.0) + wp.float64(8.0) * u[i, 4]
    film = wp.float64(0.8) + wp.float64(0.4) * u[i, 5]
    sol = wp.float64(300.0) + wp.float64(35.0) * u[i, 6]
    env = wp.float64(0.85) + wp.float64(0.3) * u[i, 7]
    view = wp.float64(0.98) + wp.float64(0.02) * u[i, 8]
    pump = wp.float64(0.8) + wp.float64(0.5) * u[i, 9]
    k = wp.float64(150.0) + wp.float64(25.0) * u[i, 10]
    T = temperatures(z[0], z[1], z[2], eps, R, H, pm, dt, film, env, view, pump, k, p, fe, tab, wp.float64(.6)+wp.float64(.8)*u[i,11], wp.float64(.95)+wp.float64(.10)*u[i,12], wp.float64(.8)+wp.float64(.4)*u[i,13])
    out[i, 0] = T[0]
    out[i, 1] = T[1]
    out[i, 2] = T[2]
    peak = (wp.float64(252000.0) + p[17] * pump * (wp.float64(20.0) / dt) * (wp.float64(20.0) / dt)) / pm
    out[i, 3] = z[3] * sol - peak

@wp.kernel
def objective(z: wp.array(dtype=wp.float64), p: wp.array(dtype=wp.float64), fe: wp.array(dtype=wp.float64), tab: wp.array(dtype=wp.float64), penalty: wp.float64, loss: wp.array(dtype=wp.float64), metrics: wp.array(dtype=wp.float64)):
    n = wp.float64(112.0) + (p[34]-wp.float64(112.0)) * z[0]
    L = wp.float64(0.008979199202278047) + wp.float64(0.01730559893637073) * z[1]
    t = wp.float64(0.0001) + wp.float64(0.0004) * z[2]
    T = temperatures(n, L, t, wp.float64(0.92), wp.float64(14.22), wp.float64(18.0), wp.float64(0.92), wp.float64(20.0), wp.float64(1.0), wp.float64(1.0), wp.float64(1.0), wp.float64(1.0), wp.float64(167.0), p, fe, tab, wp.float64(1.), wp.float64(1.), wp.float64(1.))
    rad = radiator_mass(n, L, t)
    g = wp.max(wp.float64(0.0), (T[0] - p[32]) / wp.float64(10.0))
    h = wp.max(wp.float64(0.0), (T[2] - p[33]) / wp.float64(10.0))
    loss[0] = rad / wp.float64(100.0) + penalty * (g * g + h * h)
    metrics[0] = n
    metrics[1] = L
    metrics[2] = t
    metrics[3] = T[0]
    metrics[4] = T[2]
    metrics[5] = rad
