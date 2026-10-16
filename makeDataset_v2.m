% =========================================================================
% makeDataset_v2.m
% Simulated MARG (accel/gyro/mag) + GPS dataset generator for the
% deep-learning IMU/GPS sensor-fusion thesis.
%
% This is a refactor of the original makeDataset.m. The simulation logic
% (insfilterMARG + imuSensor + gpsSensor over the LoggedQuadcopter
% trajectory) is preserved so results remain comparable, but the script
% is parameterized, reproducible, better documented, and it additionally
% logs a diagnostics file with the *filter-estimated* previous state, so
% that later experiments can compare teacher-forcing (ground-truth
% previous state) against a realistic (estimated) previous state.
%
% IMPORTANT METHODOLOGICAL NOTE (documented on purpose):
%   The training columns prev_state_* are taken from the GROUND-TRUTH
%   trajectory at time (t-1), i.e. trajPos(fcnt-1) and trajOrient(fcnt-1).
%   This is a *teacher-forcing* setup: at training time the network is
%   handed the true previous state. In closed-loop operation the network
%   must instead consume its own previous prediction, which accumulates
%   drift. The v2 training notebook therefore evaluates BOTH the
%   teacher-forced error and an autoregressive (closed-loop) error.
%
%   LIMITATION: a single trajectory (LoggedQuadcopter) is used. Only the
%   sensor-noise realization changes with the RNG seed; the underlying
%   motion is identical, so generalization across trajectories cannot be
%   claimed from this dataset alone.
% =========================================================================

clear; clc; close all;

%% ------------------------------- CONFIG ---------------------------------
% All paths are local to this script (project root). No MATLAB Examples
% folder is referenced. Helpers live in matlab_helpers/; the trajectory
% file is LoggedQuadcopter.mat next to this script.
thisDir     = fileparts(mfilename('fullpath'));
helpersDir  = fullfile(thisDir, 'matlab_helpers');
addpath(helpersDir);

cfg.imuFs            = 160;                 % IMU sample rate [Hz]
cfg.gpsFs            = 1;                    % GPS sample rate [Hz]
cfg.refloc           = [42.2825 -72.3430 53.0352]; % lat[deg] lon[deg] alt[m]
cfg.secondsToSim     = 142;                 % LoggedQuadcopter ~142 s
cfg.seed             = 1;                    % RNG seed (sensor-noise realization)
cfg.warmupSamples    = 160;                 % skip first second (filter settling)
cfg.trajFile         = fullfile(thisDir, 'LoggedQuadcopter.mat');
cfg.outFile          = fullfile(thisDir, 'dataset_v2.csv');
cfg.diagFile         = fullfile(thisDir, 'dataset_v2_filterstate.csv');
cfg.writeDiagnostics = true;
cfg.useScopes        = false;   % baseline error/pose figures (slow)

imuSamplesPerGPS = cfg.imuFs / cfg.gpsFs;
assert(imuSamplesPerGPS == fix(imuSamplesPerGPS), ...
    'GPS sampling rate must be an integer factor of IMU sampling rate.');

%% --------------------------- LOAD TRAJECTORY ----------------------------
if ~isfile(cfg.trajFile)
    error(['Could not find %s. Copy LoggedQuadcopter.mat next to ' ...
           'makeDataset_v2.m (project root).'], cfg.trajFile);
end
load(cfg.trajFile, 'trajData');
trajOrient = trajData.Orientation;
trajVel    = trajData.Velocity;
trajPos    = trajData.Position;
trajAcc    = trajData.Acceleration;
trajAngVel = trajData.AngularVelocity;

rng(cfg.seed);  % reproducible sensor-noise realization

%% ----------------------------- SENSORS ----------------------------------
% GPS
gps = gpsSensor('UpdateRate', cfg.gpsFs);
gps.ReferenceLocation        = cfg.refloc;
gps.DecayFactor              = 0.5;   % random-walk noise parameter
gps.HorizontalPositionAccuracy = 1.6;
gps.VerticalPositionAccuracy   = 1.6;
gps.VelocityAccuracy           = 0.1;

% IMU (accel + gyro + mag)
imu = imuSensor('accel-gyro-mag', 'SampleRate', cfg.imuFs);
imu.MagneticField = [19.5281 -5.0741 48.0067];

imu.Accelerometer.MeasurementRange = 19.6133;
imu.Accelerometer.Resolution       = 0.0023928;
imu.Accelerometer.ConstantBias     = 0.19;
imu.Accelerometer.NoiseDensity     = 0.0012356;

imu.Gyroscope.MeasurementRange  = deg2rad(250);
imu.Gyroscope.Resolution        = deg2rad(0.0625);
imu.Gyroscope.ConstantBias      = deg2rad(3.125);
imu.Gyroscope.AxesMisalignment  = 1.5;
imu.Gyroscope.NoiseDensity      = deg2rad(0.025);

imu.Magnetometer.MeasurementRange = 1000;
imu.Magnetometer.Resolution       = 0.1;
imu.Magnetometer.ConstantBias     = 100;
imu.Magnetometer.NoiseDensity     = 0.3 / sqrt(50);

%% --------------------------- FUSION FILTER ------------------------------
fusionfilt = insfilterMARG;
fusionfilt.IMUSampleRate     = cfg.imuFs;
fusionfilt.ReferenceLocation = cfg.refloc;

% Initial state (22-vector). insfilterMARG state layout (from the MathWorks
% "IMU and GPS Fusion for Inertial Navigation" example):
%   State                            Units   Index
%   Orientation (quaternion)                 1:4
%   Position (NED)                   m        5:7     <- DL position target frame
%   Velocity (NED)                  m/s      8:10
%   Delta Angle Bias (XYZ)          rad      11:13
%   Delta Velocity Bias (XYZ)       m/s      14:16
%   Geomagnetic Field Vector (NED)  uT       17:19
%   Magnetometer Bias (XYZ)         uT       20:22
% Ground truth seeds the initial state so the filter converges quickly.
initstate       = zeros(22,1);
initstate(1:4)  = compact(meanrot(trajOrient(1:100)));
initstate(5:7)  = mean(trajPos(1:100,:), 1);
initstate(8:10) = mean(trajVel(1:100,:), 1);
initstate(11:13)= imu.Gyroscope.ConstantBias    ./ cfg.imuFs;
initstate(14:16)= imu.Accelerometer.ConstantBias ./ cfg.imuFs;
initstate(17:19)= imu.MagneticField;
initstate(20:22)= imu.Magnetometer.ConstantBias;
fusionfilt.State = initstate;

% Measurement noises
Rmag = 0.0862;   % magnetometer
Rvel = 0.0051;   % GPS velocity
Rpos = 5.169;    % GPS position

% Process noises
fusionfilt.AccelerometerBiasNoise = 0.010716;
fusionfilt.AccelerometerNoise     = 9.7785;
fusionfilt.GyroscopeBiasNoise     = 1.3436e-14;
fusionfilt.GyroscopeNoise         = 0.00016528;
fusionfilt.MagnetometerBiasNoise  = 2.189e-11;
fusionfilt.GeomagneticVectorNoise = 7.67e-13;
fusionfilt.StateCovariance        = 1e-9 * eye(22);

%% ------------------------------ SIM LOOP --------------------------------
numsamples = cfg.secondsToSim * cfg.imuFs;
loopBound  = floor(numsamples / cfg.imuFs) * cfg.imuFs; % whole GPS seconds

% Logs for post-processing / diagnostics
pqorient = quaternion.zeros(loopBound,1);   % filter-estimated orientation
pqpos    = zeros(loopBound,3);              % filter-estimated position

% ---- optional baseline scopes (classical insfilterMARG visualization) ----
% Local copies in matlab_helpers/ (HelperScrollingPlotter, HelperPoseViewer,
% HelperPositionViewer). Handy for classical-filter baseline figures; they
% slow the simulation, so they are OFF by default (cfg.useScopes).
if cfg.useScopes
    errscope = HelperScrollingPlotter('NumInputs', 4, 'TimeSpan', 10, ...
        'SampleRate', cfg.imuFs, ...
        'YLabel', {'degrees','meters','meters','meters'}, ...
        'Title',  {'Quaternion Distance','Position X Error', ...
                   'Position Y Error','Position Z Error'}, ...
        'YLimits', [-3 3; -2 2; -2 2; -2 2]);
    posescope = HelperPoseViewer('XPositionLimits', [-15 15], ...
        'YPositionLimits', [-15 15], 'ZPositionLimits', [-10 10], ...
        'ReferenceFrame', 'NED');
end

% 26-column training matrix, identical layout to the original:
%  1: 3  accel (x y z)
%  4: 6  gyro  (x y z)
%  7: 9  mag   (x y z)     (zero-order-hold at GPS rate)
% 10:12  gps velocity (x y z)  (zero-order-hold at GPS rate)
% 13:15  GT position at t-1   (LABEL only: train_v2 Option A uses this
% 16:19  GT quaternion at t-1  to form Δpos, Δq — NOT as a network input)
% 20:22  GT position at t
% 23:26  GT quaternion at t
dataset = zeros(loopBound, 26);

gpsvel   = zeros(1,3);   % defined before first use (ZOH)
mag_hold = zeros(1,3);
fcnt = 1;

while (fcnt <= loopBound)
    % ---- predict loop at IMU rate ----
    for ff = 1:imuSamplesPerGPS
        [accel, gyro, mag] = imu(trajAcc(fcnt,:), trajAngVel(fcnt,:), ...
                                 trajOrient(fcnt));

        % Build a training row once past the warm-up second.
        if fcnt > cfg.warmupSamples
            [pw,px,py,pz] = parts(trajOrient(fcnt-1,:));  % prev (t-1) GT quat
            [cw,cx,cy,cz] = parts(trajOrient(fcnt,:));    % curr (t)   GT quat

            dataset(fcnt,:) = [accel, gyro, mag_hold, gpsvel, ...
                               trajPos(fcnt-1,:), pw, px, py, pz, ...
                               trajPos(fcnt,:),   cw, cx, cy, cz];
        end

        % Filter prediction step.
        predict(fusionfilt, accel, gyro);
        [fusedPos, fusedOrient] = pose(fusionfilt);
        pqorient(fcnt) = fusedOrient;
        pqpos(fcnt,:)  = fusedPos;

        % Optional streaming baseline error/pose scopes.
        if cfg.useScopes
            orientErr = rad2deg(dist(fusedOrient, trajOrient(fcnt)));
            posErr    = fusedPos - trajPos(fcnt,:);
            errscope(orientErr, posErr(1), posErr(2), posErr(3));
            posescope(pqpos(fcnt,:), pqorient(fcnt), ...
                      trajPos(fcnt,:), trajOrient(fcnt,:));
        end

        fcnt = fcnt + 1;
    end

    % ---- correction step at GPS rate ----
    [lla, gpsvel] = gps(trajPos(fcnt,:), trajVel(fcnt,:));
    fusegps(fusionfilt, lla, Rpos, gpsvel, Rvel);
    % Only ONE magnetometer sample per GPS second is fused (per the MathWorks
    % example: "only 1 of every 160 magnetometer samples is given to the
    % fusion algorithm"). The dataset therefore stores this same low-rate,
    % zero-order-held magnetometer value in its mag channels, so the network
    % sees exactly what the filter fused.
    fusemag(fusionfilt, mag, Rmag);
    mag_hold = mag;   % zero-order-hold the last fused magnetometer reading
end

%% ---------------------------- WRITE OUTPUT ------------------------------
% Drop warm-up rows (first second) that were left as zeros.
dataset = dataset(cfg.warmupSamples+1:end, :);
writematrix(dataset, cfg.outFile);
fprintf('Wrote %d rows x %d cols to %s\n', size(dataset,1), size(dataset,2), cfg.outFile);

% Diagnostics: filter-estimated previous state vs. ground truth.
% Columns: time, fusedPos(3), fusedQuat(4), gtPos(3), gtQuat(4)
if cfg.writeDiagnostics
    idx  = (1:loopBound).';
    time = (idx-1) / cfg.imuFs;
    fq   = compact(pqorient(1:loopBound));                 % N x 4
    gq   = compact(trajOrient(1:loopBound));               % N x 4
    diag = [time, pqpos(1:loopBound,:), fq, ...
            trajPos(1:loopBound,:), gq];
    writematrix(diag, cfg.diagFile);
    fprintf('Wrote diagnostics (%d rows) to %s\n', size(diag,1), cfg.diagFile);
end

%% -------------------------- ERROR COMPUTATION ---------------------------
posd  = pqpos(1:loopBound,:) - trajPos(1:loopBound,:);
quatd = rad2deg(dist(pqorient(1:loopBound), trajOrient(1:loopBound)));

fprintf('\nEnd-to-End Simulation Position RMS Error\n');
msep = sqrt(mean(posd.^2));
fprintf('\tX: %.2f , Y: %.2f, Z: %.2f   (meters)\n', msep(1), msep(2), msep(3));

fprintf('End-to-End Quaternion Distance RMS Error (degrees)\n');
fprintf('\t%.2f (degrees)\n\n', sqrt(mean(quatd.^2)));
