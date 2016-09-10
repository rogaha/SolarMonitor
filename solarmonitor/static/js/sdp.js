var sdp = angular.module('sdpApp', []);

sdp.config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('[[').endSymbol(']]');
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
