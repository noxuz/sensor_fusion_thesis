clear;clc;close all;
imuFs = 160;
gpsFs = 1;

% Define where on the Earth this simulated scenario takes place using the
% latitude, longitude and altitude.
refloc = [42.2825 -72.3430 53.0352];


% Validate that the |gpsFs| divides |imuFs|. This allows the sensor sample 
% rates to be simulated using a nested for loop without complex sample rate
% matching.
imuSamplesPerGPS = (imuFs/gpsFs);

% Declarar filtro
fusionfilt = insfilterMARG;
fusionfilt.IMUSampleRate = imuFs;
fusionfilt.ReferenceLocation = refloc;

% Cargar datos y asignar
load LoggedQuadcopter.mat trajData;
trajOrient = trajData.Orientation;
trajVel = trajData.Velocity;
trajPos = trajData.Position;
trajAcc = trajData.Acceleration;
trajAngVel = trajData.AngularVelocity;

% Initialize the random number generator used in the simulation of sensor
% noise.
rng(1)

% Arrancar sensor GPS y definir params
gps = gpsSensor('UpdateRate', gpsFs);
gps.ReferenceLocation = refloc;     
gps.DecayFactor = 0.5;              % Random walk noise parameter 
gps.HorizontalPositionAccuracy = 1.6;   
gps.VerticalPositionAccuracy =  1.6;
gps.VelocityAccuracy = 0.1;

% Arrancar sensor IMU
imu = imuSensor('accel-gyro-mag', 'SampleRate', imuFs);
imu.MagneticField = [19.5281 -5.0741 48.0067];

% Definir parametros de sensor IMU
% Accelerometer
imu.Accelerometer.MeasurementRange =  19.6133;
imu.Accelerometer.Resolution = 0.0023928;
imu.Accelerometer.ConstantBias = 0.19;
imu.Accelerometer.NoiseDensity = 0.0012356;

% Gyroscope
imu.Gyroscope.MeasurementRange = deg2rad(250);
imu.Gyroscope.Resolution = deg2rad(0.0625);
imu.Gyroscope.ConstantBias = deg2rad(3.125);
imu.Gyroscope.AxesMisalignment = 1.5;
imu.Gyroscope.NoiseDensity = deg2rad(0.025);

% Magnetometer
imu.Magnetometer.MeasurementRange = 1000;
imu.Magnetometer.Resolution = 0.1;
imu.Magnetometer.ConstantBias = 100;
imu.Magnetometer.NoiseDensity = 0.3/ sqrt(50);

%% Arrancar initial state of this 
% Initialize the states of the filter 

initstate = zeros(22,1);
initstate(1:4) = compact( meanrot(trajOrient(1:100))); 
initstate(5:7) = mean( trajPos(1:100,:), 1);
initstate(8:10) = mean( trajVel(1:100,:), 1);
initstate(11:13) =  imu.Gyroscope.ConstantBias./imuFs;
initstate(14:16) =  imu.Accelerometer.ConstantBias./imuFs;
initstate(17:19) =  imu.MagneticField;
initstate(20:22) = imu.Magnetometer.ConstantBias;

fusionfilt.State = initstate;

%% Definir parametros de ruido de sensores para MARG
% Measurement noises
Rmag = 0.0862; % Magnetometer measurement noise
Rvel = 0.0051; % GPS Velocity measurement noise
Rpos = 5.169; % GPS Position measurement noise

% Process noises
fusionfilt.AccelerometerBiasNoise =  0.010716; 
fusionfilt.AccelerometerNoise = 9.7785; 
fusionfilt.GyroscopeBiasNoise = 1.3436e-14; 
fusionfilt.GyroscopeNoise =  0.00016528; 
fusionfilt.MagnetometerBiasNoise = 2.189e-11;
fusionfilt.GeomagneticVectorNoise = 7.67e-13;

% Initial error covariance
fusionfilt.StateCovariance = 1e-9*eye(22);


%% Simulacion?
% Loop setup - |trajData| has about 142 seconds of recorded data.
secondsToSimulate = 142; % simulate about 50 seconds
numsamples = secondsToSimulate*imuFs;

loopBound = floor(numsamples);
loopBound = floor(loopBound/imuFs)*imuFs; % ensure enough IMU Samples

% Log data for final metric computation.
pqorient = quaternion.zeros(loopBound,1);
pqpos = zeros(loopBound,3);

fcnt = 1;

% Save for dataset
dataset = zeros([loopBound 26]);

while(fcnt <=loopBound)
    % |predict| loop at IMU update frequency.
    for ff=1:imuSamplesPerGPS
        % Simulate the IMU data from the current pose.
        [accel, gyro, mag] = imu(trajAcc(fcnt,:), trajAngVel(fcnt, :), ...
            trajOrient(fcnt));

        % Form dataset
        if fcnt>160
            [a,b,c,d] = parts(trajOrient(fcnt-1,:));
            [e,f,g,h] = parts(trajOrient(fcnt,:));

            dataset(fcnt,:) = [accel, gyro, mag_hold, gpsvel, trajPos(fcnt-1,:),a,b,c,d...
                               trajPos(fcnt,:), e,f,g,h];
        end

        % Use the |predict| method to estimate the filter state based
        % on the simulated accelerometer and gyroscope signals.
        predict(fusionfilt, accel, gyro);
        
        % Acquire the current estimate of the filter states.
        [fusedPos, fusedOrient] = pose(fusionfilt);
        
        % Save the position and orientation for post processing.
        pqorient(fcnt) = fusedOrient;
        pqpos(fcnt,:) = fusedPos;
        
        fcnt = fcnt + 1;
    end

    % This next step happens at the GPS sample rate.
    % Simulate the GPS output based on the current pose.
    [lla, gpsvel] = gps( trajPos(fcnt,:), trajVel(fcnt,:) );
    
    % Correct the filter states based on the GPS data and magnetic
    % field measurements.
    fusegps(fusionfilt, lla, Rpos, gpsvel, Rvel);
    fusemag(fusionfilt, mag, Rmag);
    % zoh val
    mag_hold = mag;
 
end

% Remove 0 entriers firsts,
dataset = dataset(161:end,:);
writematrix(dataset,"dataset.csv")

% Error computation
posd = pqpos(1:loopBound,:) - trajPos( 1:loopBound, :);

% For orientation, quaternion distance is a much better alternative to
% subtracting Euler angles, which have discontinuities. The quaternion
% distance can be computed with the |dist| function, which gives the
% angular difference in orientation in radians. Convert to degrees
% for display in the command window. 

quatd = rad2deg(dist(pqorient(1:loopBound), trajOrient(1:loopBound)) );

% Display RMS errors in the command window.
fprintf('\n\nEnd-to-End Simulation Position RMS Error\n');

msep = sqrt(mean(posd.^2));
fprintf('\tX: %.2f , Y: %.2f, Z: %.2f   (meters)\n\n',msep(1), ...
    msep(2), msep(3));

fprintf('End-to-End Quaternion Distance RMS Error (degrees) \n');
fprintf('\t%.2f (degrees)\n\n', sqrt(mean(quatd.^2)));