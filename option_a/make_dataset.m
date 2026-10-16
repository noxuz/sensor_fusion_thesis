% Option A dataset: noisy MARG + GPS vel, GT pose, and insfilterMARG log.
% Rows: accel(3) gyro(3) mag(3) gpsvel(3) gt_pos(3) gt_quat_wxyz(4)

clear; clc; close all;

thisDir = fileparts(mfilename('fullpath'));

imuFs = 160;
gpsFs = 1;
refloc = [42.2825 -72.3430 53.0352];
secondsToSim = 142;
warmup = 160;
seed = 1;

imuSamplesPerGPS = imuFs / gpsFs;
assert(imuSamplesPerGPS == fix(imuSamplesPerGPS));

trajFile = fullfile(thisDir, 'LoggedQuadcopter.mat');
if ~isfile(trajFile)
    error('Missing %s', trajFile);
end
load(trajFile, 'trajData');
trajOrient = trajData.Orientation;
trajVel    = trajData.Velocity;
trajPos    = trajData.Position;
trajAcc    = trajData.Acceleration;
trajAngVel = trajData.AngularVelocity;

rng(seed);

gps = gpsSensor('UpdateRate', gpsFs);
gps.ReferenceLocation = refloc;
gps.DecayFactor = 0.5;
gps.HorizontalPositionAccuracy = 1.6;
gps.VerticalPositionAccuracy = 1.6;
gps.VelocityAccuracy = 0.1;

imu = imuSensor('accel-gyro-mag', 'SampleRate', imuFs);
imu.MagneticField = [19.5281 -5.0741 48.0067];
imu.Accelerometer.MeasurementRange = 19.6133;
imu.Accelerometer.Resolution = 0.0023928;
imu.Accelerometer.ConstantBias = 0.19;
imu.Accelerometer.NoiseDensity = 0.0012356;
imu.Gyroscope.MeasurementRange = deg2rad(250);
imu.Gyroscope.Resolution = deg2rad(0.0625);
imu.Gyroscope.ConstantBias = deg2rad(3.125);
imu.Gyroscope.AxesMisalignment = 1.5;
imu.Gyroscope.NoiseDensity = deg2rad(0.025);
imu.Magnetometer.MeasurementRange = 1000;
imu.Magnetometer.Resolution = 0.1;
imu.Magnetometer.ConstantBias = 100;
imu.Magnetometer.NoiseDensity = 0.3 / sqrt(50);

fusionfilt = insfilterMARG;
fusionfilt.IMUSampleRate = imuFs;
fusionfilt.ReferenceLocation = refloc;

initstate = zeros(22, 1);
initstate(1:4)   = compact(meanrot(trajOrient(1:100)));
initstate(5:7)   = mean(trajPos(1:100, :), 1);
initstate(8:10)  = mean(trajVel(1:100, :), 1);
initstate(11:13) = imu.Gyroscope.ConstantBias ./ imuFs;
initstate(14:16) = imu.Accelerometer.ConstantBias ./ imuFs;
initstate(17:19) = imu.MagneticField;
initstate(20:22) = imu.Magnetometer.ConstantBias;
fusionfilt.State = initstate;

Rmag = 0.0862;
Rvel = 0.0051;
Rpos = 5.169;
fusionfilt.AccelerometerBiasNoise = 0.010716;
fusionfilt.AccelerometerNoise = 9.7785;
fusionfilt.GyroscopeBiasNoise = 1.3436e-14;
fusionfilt.GyroscopeNoise = 0.00016528;
fusionfilt.MagnetometerBiasNoise = 2.189e-11;
fusionfilt.GeomagneticVectorNoise = 7.67e-13;
fusionfilt.StateCovariance = 1e-9 * eye(22);

loopBound = floor(secondsToSim * imuFs / imuFs) * imuFs;
pqorient = quaternion.zeros(loopBound, 1);
pqpos = zeros(loopBound, 3);
dataset = zeros(loopBound, 19);

gpsvel = zeros(1, 3);
mag_hold = zeros(1, 3);
fcnt = 1;

while fcnt <= loopBound
    for ff = 1:imuSamplesPerGPS
        [accel, gyro, mag] = imu(trajAcc(fcnt, :), trajAngVel(fcnt, :), ...
                                 trajOrient(fcnt));
        [qw, qx, qy, qz] = parts(trajOrient(fcnt, :));
        dataset(fcnt, :) = [accel, gyro, mag_hold, gpsvel, ...
                            trajPos(fcnt, :), qw, qx, qy, qz];

        predict(fusionfilt, accel, gyro);
        [fusedPos, fusedOrient] = pose(fusionfilt);
        pqorient(fcnt) = fusedOrient;
        pqpos(fcnt, :) = fusedPos;
        fcnt = fcnt + 1;
    end
    if fcnt <= size(trajPos, 1)
        [lla, gpsvel] = gps(trajPos(fcnt, :), trajVel(fcnt, :));
        fusegps(fusionfilt, lla, Rpos, gpsvel, Rvel);
        fusemag(fusionfilt, mag, Rmag);
        mag_hold = mag;
    end
end

keep = (warmup + 1):loopBound;
t = ((keep - 1) / imuFs).';
fq = compact(pqorient(keep));
gq = compact(trajOrient(keep));

writematrix(dataset(keep, :), fullfile(thisDir, 'dataset.csv'));
writematrix([t, pqpos(keep, :), fq, trajPos(keep, :), gq], ...
    fullfile(thisDir, 'filterstate.csv'));

posd = pqpos(keep, :) - trajPos(keep, :);
quatd = rad2deg(dist(pqorient(keep), trajOrient(keep)));
msep = sqrt(mean(posd.^2));
fprintf('Wrote %d rows to dataset.csv and filterstate.csv\n', numel(keep));
fprintf('EKF pos RMSE  X %.2f  Y %.2f  Z %.2f m\n', msep(1), msep(2), msep(3));
fprintf('EKF quat RMSE %.2f deg\n', sqrt(mean(quatd.^2)));
