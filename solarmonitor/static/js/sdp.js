var sdp = angular.module('sdpApp', []);

sdp.config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('[[').endSymbol(']]');
});

sdp.constant("moment", moment);

sdp.controller('eventController', function($scope, $http) {

    $scope.today = moment().subtract(1, 'days');
    $scope.getEvents = function(daysAgo) {
        console.log(daysAgo)
        $scope.startDate = moment().subtract((1 + daysAgo), 'days').format("YYYY-MM-DD");
        console.log($scope.startDate)
        $http.get('/users/dashboard/status/events/' + $scope.startDate + '/' + $scope.today.format("YYYY-MM-DD"))
            .then(function(response) {
                $scope.events = response.data
            });
    }
    $scope.events = $scope.getEvents(7)
});

sdp.controller('progressBar', function($scope, $http, $timeout) {
    $scope.taskSuccess = null
    $scope.taskProgress = null
    $scope.value = 0;

    $scope.watchedTasks = []

    var poll = function() {
        $timeout(function() {

            $http.get('/users/dashboard/status/task_check')
                .then(function(response) {
                    console.log(response.data)
                    if (response.data.length > 0) {
                        $scope.watchedTasks.push(response.data)
                    }
                });

            poll();
        }, 1000);
    };


    var check_status = function() {
        $timeout(function() {

            //$http.get('/users/dashboard/status/task_check')
            //    .then(function(response) {
            //        console.log(response.data)
            //        if (response.data.length > 0) {
            //            $scope.watchedTasks.push(response.data)
            //        }
            //    });

            //check_status();
        }, 1000);
    };


    check_status();
    poll();

});
